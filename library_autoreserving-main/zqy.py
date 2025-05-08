import requests
from datetime import datetime, time as dt_time
import time
import logging
import sys
import os
import concurrent.futures
from requests.adapters import HTTPAdapter

# ============== 配置区域（根据你的抓包数据修改）===============#随便用什么抓包软件就可以抓到cookies，seats改也很容易。把seats设成自己想要的就可以直接用了
CONFIG = {
    "cookies": {
        "ASP.NET_SessionId": "3bnerus44v3v0f5aazad1a0y",#没记错的话只要更新这一条就好
        "cookie_unit_name": "%e6%b9%96%e5%8d%97%e5%86%9c%e4%b8%9a%e5%a4%a7%e5%ad%a6%e5%9b%be%e4%b9%a6%e9%a6%86",#不用更换
        "cookie_come_app": "D935AE54952F16C1",#不要更换
        "cookie_come_timestamp": "1744270472",#这个也可以不更新
        "cookie_come_sno": "xxxxx",#下面这两个是身份信息
        "dt_cookie_user_name_remember": "xxxxx"
    },
    "seats": [
        #求求不要约这个几个座位，这是我帮自己和朋友约的常用座位嘿嘿
        {"seatno": "HNND20478", "seatname": "478", "datetime": "510,1320"},
        {"seatno": "HNND20406", "seatname": "406", "datetime": "570,1320"},
        {"seatno": "HNND20401", "seatname": "401", "datetime": "570,1320"},
        {"seatno": "HNND20479", "seatname": "479", "datetime": "510,1320"},
        {"seatno": "HNND20476", "seatname": "477", "datetime": "510,1320"},
    ],
    "request_timeout": 10,
    "max_attempts": 10
}

# ============== 日志配置 ================#不用管，这是我在本地测试用的
LOG_DIR = r"D:\\course_resource\\图书馆预约自动化\\logging"
os.makedirs(LOG_DIR, exist_ok=True)
current_date = datetime.now().strftime("%Y%m%d")
LOG_FILE = os.path.join(LOG_DIR, f"library_booking_{current_date}.log")
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(formatter)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class LibraryBooker:
    def __init__(self, config):
        self.base_url = "http://libseat.hunau.edu.cn/apim/seat/SeatDateHandler.ashx"
        self.session = requests.Session()
        self._init_session(config)

    def _init_session(self, config):
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "http://libseat.hunau.edu.cn/mobile/html/seat/seatquickbook.html",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        cookies = requests.utils.cookiejar_from_dict(config["cookies"])
        self.session.cookies.update(cookies)
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def book_seat(self, seat_info):
        payload = {
            "data_type": "seatDate",
            "seatno": seat_info["seatno"],
            "seatname": seat_info["seatname"],
            "seatdate": "tomorrow",####可以选择today和tomorrow，预约今天和明天。由于我一般约第二天的这里设置tomorrow就好
            "datetime": seat_info["datetime"]
        }
        for attempt in range(CONFIG["max_attempts"]):#改成并发请求了，可以同时请求多个座位。但这样就有随机性，不一定能预约到最想要的那个。可以改改上面只设置一个座位
            try:
                response = self.session.post(
                    self.base_url,
                    data=payload,
                    timeout=CONFIG["request_timeout"]
                )
                logger.info("预约请求响应：%s", response.text)
                if response.status_code == 200:
                    json_data = response.json()
                    if json_data.get("code") == 0:
                        logger.info("✅ 预约成功！座位：%s，响应数据：%s", seat_info["seatname"], json_data)
                        return True
                    else:
                        logger.error("❌ 预约失败：座位：%s，错误信息：%s", seat_info["seatname"],
                                     json_data.get("msg", "未知错误"))
                else:
                    logger.error("预约请求失败，状态码：%d", response.status_code)
            except Exception as e:
                logger.error("⚠️ 请求异常：座位：%s，错误：%s", seat_info["seatname"], str(e))
        return False


if __name__ == "__main__":
    booker = LibraryBooker(CONFIG)
    logger.info("程序已启动，等待预约时间窗口...")

    start_time = dt_time(21, 59, 0)#这里得用UTC时间设置，我设置的是5:59开始发送请求。
    end_time = dt_time(22, 4, 0)

    while True:
        now = datetime.now()
        current_time = now.time()

        if current_time > end_time:
            logger.info("时间窗口已过，程序退出")
            sys.exit()

        if start_time <= current_time <= end_time:
            logger.info("🕒 进入预约时间窗口，开始并发尝试...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                future_to_seat = {executor.submit(booker.book_seat, seat): seat for seat in CONFIG["seats"]}
                for future in concurrent.futures.as_completed(future_to_seat):
                    seat = future_to_seat[future]
                    try:
                        result = future.result()
                        if result:
                            logger.info("🎉 成功预约座位：%s", seat["seatname"])
                    except Exception as e:
                        logger.error("并发请求异常：%s", str(e))
        else:
            time.sleep(0.1)
