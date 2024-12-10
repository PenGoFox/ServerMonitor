import json
import time
import shutil

from Shouter import *
from Logger import *
import LuBoJi # 录播姬

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

if "__main__" == __name__:
    logger = initAndGetLogger(loglevel=logging.DEBUG)

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

    luConf = config["luboji"]
    lu = LuBoJi.LuBoJi(luConf["url"], luConf["username"], luConf["password"])

    lastLoopData = {
        "streaming": False,
        "lastTimeCheckUsage": time.time()
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
            if shouter.send(title, desc, short):
                logger.info("发送开播通知成功")
            else:
                logger.error("发送开播通知失败")
        lastLoopData["streaming"] = streaming

        # 检查硬盘空间使用情况
        timestamp = time.time()
        if timestamp - lastLoopData["lastTimeCheckUsage"] > intrevalOfCheckDiskUsage:
            lastLoopData["lastTimeCheckUsage"] = timestamp
            total, used, free = getDiskUsage()
            threadshold = duConf["threshold"]
            logger.info("磁盘空间：共 {:.3f} GB, 已使用 {:.3f} GB, 剩余 {:.3f} GB".format(total, used, free))

            if used / total > threadshold:
                logger.info("发送磁盘空间告警通知")

                notEnoughStr = "磁盘空间已不足 {:.0f}%".format(threadshold * 100)

                title = "磁盘空间警告"
                desc = "磁盘空间告急！\n\n"
                desc = notEnoughStr + "\n\n\n\n"
                desc += "| 总空间 | 已使用 | 剩余空间 |\n"
                desc += "| ---- | ---- | ---- |\n"
                desc += "| {0:.3f} GB | {1:.3f} GB | {2:.3f} GB |\n\n".format(total, used, free)
                short = notEnoughStr
                if shouter.send(title, desc, short):
                    logger.info("发送磁盘告警通知成功")
                else:
                    logger.error("发送磁盘告警通知失败")
