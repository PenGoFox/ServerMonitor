import json
import time
import shutil

from Shouter import *
from Logger import *
import LuBoJi # 录播姬

def parseTimeIntervalStr(s:str):
    '''
    把数字和时间字符串组合成的字符串解析成实际的秒数
    只管转换，值也有可能小于 0

    比如 0.5day 会解析为 43200 (0.5 * 86400 = 43200) 秒
    而字符串 20 则直接解析为数字 20

    解析失败时将抛出 ValueError 异常
    '''

    timeStrEndMatchPatterns = ["day", "hour", "minute", "second"]
    coefficientList = [86400, 3600, 60, 1]
    for idx, p in enumerate(timeStrEndMatchPatterns):
        if s.endswith(p):
            numStr = s[:-len(p)].strip() # 获取前面的数字字符串
            if numStr == "":
                return 0

            num = 0
            try:
                num = float(numStr)
            except ValueError:
                raise ValueError(f"{s} 不是正确的时间间隔表示")

            return num * coefficientList[idx]

    try:
        num = int(s)
        return num
    except ValueError:
        raise ValueError(f"{s} 不是正确的时间间隔表示")

def parseTimeInterval(val):
    if not isinstance(val, (str, int)):
        raise ValueError("时间输入值有误，只能是字符串或者数字")

    ret = -1

    if isinstance(val, int):
        ret = val
    else:
        valStr = val.strip()
        if valStr == "":
            raise ValueError("时间间隔不能为空字符串")

        ret = parseTimeIntervalStr(valStr)

    if ret <= 0:
        raise ValueError(f"\"{val}\" 的等效值有误，时间等效值不能小于等于 0")

    return ret

def getDiskUsage(path="/"):
    total, used, free = shutil.disk_usage(path)

    total = total / (2**30)
    used = used / (2**30)
    free = free / (2**30)

    return total, used, free

def loadConfig(filename):
    try:
        with open(filename) as f:
            return json.load(f)
    except:
        pass

    return None

def sendDiskUsageWarning(total, used, free, threshold):
    '''
    发送磁盘使用空间告警信息

    total       总空间
    used        已使用空间
    free        剩余空间
    threshold 报警阈值，仅用作提供文本信息，不作判断
    '''
    ratioUsed = used / total

    logger.info("发送磁盘空间告警通知")

    notEnoughStr = "磁盘空间已使用 {:.2f}% ，达到设定的阈值 {:.2f}%".format(ratioUsed * 100, threshold * 100)

    title = "磁盘空间警告"
    desc = "磁盘空间告急！\n\n"
    desc = notEnoughStr + "\n\n\n\n"
    desc += "| 总空间 | 已使用 | 剩余空间 |\n"
    desc += "| ---- | ---- | ---- |\n"
    desc += "| {0:.2f} GB | {1:.2f} GB | {2:.2f} GB |\n\n".format(total, used, free)
    short = notEnoughStr
    tags = "服务器报警"
    if shouter.send(title, desc, short, tags):
        logger.info("发送磁盘告警通知成功")
    else:
        logger.error("发送磁盘告警通知失败")

if "__main__" == __name__:
    logger = initAndGetLogger()

    configfile = "config.json"
    logger.info(f"读取配置文件 \"{configfile}\"")
    config = loadConfig(configfile)
    if config is None:
        logger.error(f"无法读取配置文件 \"{configfile}\"")
    logger.info("读取配置文件完成")

    logger.info("初始化接口")
    shouter = Shouter(config["sendkey"])
    logger.info("初始化接口完成")

    duConf = config["diskUsage"]
    thresholds = []
    if "thresholds" in duConf:
        for t in duConf["thresholds"]:
            item = {
                "threshold": t["threshold"],
                "interval": parseTimeInterval(t["interval"])
            }
            thresholds.append(item)
        thresholds.sort(key = lambda x : x["threshold"], reverse = True)
    else:
        threshold = 0.8
        interval = 3600
        if "threshold" in duConf:
            threshold = duConf["threshold"]
        if "interval" in duConf:
            interval  = parseTimeInterval(duConf["interval"])
        item = {
            "threshold": threshold,
            "interval": interval
        }
        thresholds.append(item)
    if len(thresholds) == 0:
        raise ValueError("阈值列表为空，请设置阈值列表或直接设置阈值")
    for t in thresholds:
        threshold = t["threshold"]
        if threshold <= 0 or threshold >= 1:
            raise ValueError(f"阈值 {threshold} 设置不合理，必须要大于 0 且小于 1")

    luConf = config["luboji"]
    lu = LuBoJi.LuBoJi(luConf["url"], luConf["username"], luConf["password"])

    lastLoopData = {
        "streaming": False,
        "lastTimeCheckUsage": time.time(),
        "lastTimeUsageThreshold": -1
    }

    intrevalOfCheckDiskUsage = 60 * 60 # 检查剩余空间的时间间隔

    intreval = 30 # 每一轮循环的时间间隔，单位：秒
    _isFirstLoop = True
    while True:
        if _isFirstLoop:
            _isFirstLoop = False

            if not lu.testLogin():
                logger.error("login failed!")
                break

            lastLoopData["lastTimeCheckUsage"] = time.time() - intrevalOfCheckDiskUsage - 10

        else:
            logger.debug(f"sleep {intreval} seconds")
            time.sleep(intreval)

        # 有时候会出现路由无法到达的问题，这里加一个重试机制
        _lu_retry = 0 # 重试次数
        for _retry in range(4): # 重试 4 次
            try:
                # 处理录播姬的信息
                room = lu.getRoomMessage(luConf["roomId"])
                streaming = room["streaming"]
                if streaming and not lastLoopData["streaming"]:
                    logger.info("发送开播通知")

                    upName = room["name"] # up 主名称
                    title = room["title"]
                    recording = room["recording"]
                    areaNameParent = room["areaNameParent"]
                    areaNameChild = room["areaNameChild"]

                    recordingStr = "已开始录制" if recording else "未开始录制"

                    title = "开播通知"
                    desc = f"**{upName}** 开播啦！\n\n游戏分区：{areaNameParent}-{areaNameChild}\n\n{recordingStr}"
                    short = f"{upName} 开播啦！"
                    tags = "开播信息"
                    if shouter.send(title, desc, short, tags):
                        logger.info("发送开播通知成功")
                    else:
                        logger.error("发送开播通知失败")
                lastLoopData["streaming"] = streaming
                _lu_retry = -1 # 直接成功或者重试成功时该值小于 0
                break
            except Exception as e:
                logger.error(e)
                _lu_retry += 1
            time.sleep(10) # sleep for 10 seconds
        if _lu_retry >= 0: # 直接成功或者重试成功时该值小于 0
            logger.error("tried")

        # 检查硬盘空间使用情况
        timestamp = time.time()
        total, used, free = getDiskUsage()
        ratioUsed = used / total

        def sendUsageMessage():
            lastLoopData["lastTimeCheckUsage"] = timestamp
            logger.info("磁盘空间：共 {:.3f} GB, 已使用 {:.3f} GB, 剩余 {:.3f} GB".format(total, used, free))
            sendDiskUsageWarning(total, used, free, threshold)

        threshold = -1
        for t in thresholds: # 找出当前的阈值及其对应的时间间隔
            if ratioUsed > t["threshold"]:
                intrevalOfCheckDiskUsage = t["interval"]
                threshold = t["threshold"]
                break

        if threshold > 0: # 打开阈值检测
            if threshold > lastLoopData["lastTimeUsageThreshold"]: # 阈值增加了
                # 立刻通知一遍
                sendUsageMessage()
            elif threshold < lastLoopData["lastTimeUsageThreshold"]: # 阈值减小了
                pass
            else: # 阈值没变
                if timestamp - lastLoopData["lastTimeCheckUsage"] > intrevalOfCheckDiskUsage: # 判断是不是到时间了
                    sendUsageMessage()
        lastLoopData["lastTimeUsageThreshold"] = threshold
