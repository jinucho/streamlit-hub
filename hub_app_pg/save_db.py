import os
import json
import psycopg2
from psycopg2.extras import DictCursor
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로그 설정
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "meokten_db.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

file_handler = RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.propagate = False

# PostgreSQL 연결 정보 (기본값 설정)
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")



def get_db_connection():
    """데이터베이스 연결을 생성하는 함수"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        return conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 중 오류 발생: {str(e)}")
        raise


# 데이터베이스 초기화 함수
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # restaurants 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurants (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                latitude TEXT,
                longitude TEXT,
                station_name TEXT,
                video_id TEXT UNIQUE,
                video_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # menus 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS menus (
                id SERIAL PRIMARY KEY,
                restaurant_id INTEGER REFERENCES restaurants(id),
                menu_type TEXT,
                menu_name TEXT NOT NULL,
                menu_review TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        logger.info("데이터베이스 초기화 완료")
    except Exception as e:
        conn.rollback()
        logger.error(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


# JSON 파일에서 정보 로드 함수
def load_from_json(json_file_path):
    try:
        if not os.path.exists(json_file_path):
            logger.error(f"JSON 파일이 존재하지 않습니다: {json_file_path}")
            return None

        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"JSON 파일에서 {len(data)} 개의 식당 정보 로드 완료")
        return data
    except Exception as e:
        logger.error(f"JSON 파일 로드 중 오류 발생: {str(e)}")
        return None


# 데이터베이스에 정보 저장 함수
def save_to_db(video_id, restaurant_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 식당 정보 추출
        name = restaurant_data.get("restaurant_name", "이름 없음")
        address = restaurant_data.get("address", "주소 없음")
        latitude = restaurant_data.get("latitude", "정보 없음")
        longitude = restaurant_data.get("longitude", "정보 없음")
        station_name = restaurant_data.get("station_name", "정보 없음")
        video_url = restaurant_data.get("video_url")
        if not video_url:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        # URL 끝에 % 문자가 있으면 제거
        if video_url and video_url.endswith("%"):
            video_url = video_url[:-1]

        # 이미 존재하는 video_id인지 확인
        cursor.execute("SELECT id FROM restaurants WHERE video_id = %s", (video_id,))
        existing_restaurant = cursor.fetchone()

        if existing_restaurant:
            logger.info(f"이미 존재하는 데이터 패스: video_id {video_id}")
            return True  # 이미 존재하는 데이터는 패스

        # 식당 정보 저장
        cursor.execute(
            """
            INSERT INTO restaurants (name, address, latitude, longitude, station_name, video_id, video_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (name, address, latitude, longitude, station_name, video_id, video_url),
        )

        # 방금 삽입한 식당의 ID 가져오기
        restaurant_id = cursor.fetchone()[0]

        # 메뉴 정보 저장
        menus = restaurant_data.get("menus", [])
        for menu in menus:
            menu_type = menu.get("menu_type", "알 수 없음")
            menu_name = menu.get("menu_name", "이름 없음")
            menu_review = menu.get("menu_review", "")

            cursor.execute(
                """
                INSERT INTO menus (restaurant_id, menu_type, menu_name, menu_review)
                VALUES (%s, %s, %s, %s)
            """,
                (restaurant_id, menu_type, menu_name, menu_review),
            )

        conn.commit()
        logger.info(
            f"식당 '{name}' 정보 저장 완료 (ID: {restaurant_id}, 메뉴 수: {len(menus)})"
        )
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"데이터베이스 저장 중 오류 발생 (video_id: {video_id}): {str(e)}")
        return False

    finally:
        cursor.close()
        conn.close()


# 여러 식당 정보를 처리하는 함수
def save_multiple_restaurants(video_id, restaurants_list):
    success_count = 0
    error_count = 0

    for idx, restaurant_data in enumerate(restaurants_list):
        # 각 식당에 고유 식별자 추가 (video_id_idx 형식)
        unique_video_id = f"{video_id}_{idx}"

        # 비디오 URL 설정
        if "video_url" not in restaurant_data:
            restaurant_data["video_url"] = f"https://www.youtube.com/watch?v={video_id}"

        if save_to_db(unique_video_id, restaurant_data):
            success_count += 1
        else:
            error_count += 1

    return success_count, error_count


# 데이터베이스 조회 함수 (테스트용)
def query_db():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        # 식당 정보 조회
        logger.info("=== 저장된 식당 정보 ===")
        cursor.execute("SELECT COUNT(*) as count FROM restaurants")
        total_count = cursor.fetchone()["count"]
        logger.info(f"총 식당 수: {total_count}")

        cursor.execute("SELECT * FROM restaurants LIMIT 5")
        restaurants = cursor.fetchall()

        for r in restaurants:
            logger.info(
                f"ID: {r['id']}, 이름: {r['name']}, 주소: {r['address']}, URL: {r['video_url']}"
            )

            # 해당 식당의 메뉴 조회
            cursor.execute("SELECT * FROM menus WHERE restaurant_id = %s", (r["id"],))
            menus = cursor.fetchall()

            logger.info(f"  메뉴 수: {len(menus)}")
            for m in menus:
                logger.info(f"  - {m['menu_name']} ({m['menu_type']})")

        # 메뉴 통계
        cursor.execute("SELECT COUNT(*) as count FROM menus")
        total_menus = cursor.fetchone()["count"]
        logger.info(f"총 메뉴 수: {total_menus}")

    finally:
        cursor.close()
        conn.close()


# 메인 함수
def main():
    # 데이터베이스 초기화
    init_db()

    # JSON 파일 경로
    json_file_path = "./data/meokten_restaurants.json"

    # 파일이 없으면 대체 경로 시도
    if not os.path.exists(json_file_path):
        json_file_path = "all_restaurants.json"
        if not os.path.exists(json_file_path):
            logger.error("JSON 파일을 찾을 수 없습니다.")
            return

    # JSON 파일에서 데이터 로드
    restaurants_data = load_from_json(json_file_path)
    if not restaurants_data:
        return

    success_count = 0
    error_count = 0
    problem_videos = []

    # 각 식당 정보를 데이터베이스에 저장
    logger.info(f"총 {len(restaurants_data)} 개의 항목을 처리합니다.")

    # 데이터 형식 확인 및 처리
    if isinstance(restaurants_data, list):
        logger.info("리스트 형식의 JSON 데이터 감지됨")

        for restaurant_data in restaurants_data:
            # 필수 필드 확인
            if "video_id" not in restaurant_data:
                logger.warning(
                    f"video_id 필드가 없는 데이터 발견: {restaurant_data.get('restaurant_name', '이름 없음')}"
                )
                error_count += 1
                continue

            video_id = restaurant_data["video_id"]
            logger.info(f"처리 중: {video_id}")

            # 데이터베이스에 저장
            if save_to_db(video_id, restaurant_data):
                success_count += 1
            else:
                error_count += 1
                problem_videos.append(video_id)

    elif isinstance(restaurants_data, dict):
        logger.info("딕셔너리 형식의 JSON 데이터 감지됨")

        for video_id, restaurant_data in restaurants_data.items():
            logger.info(f"처리 중: {video_id}")

            # 여러 식당 정보가 있는 경우 (리스트 형식)
            if isinstance(restaurant_data, list):
                logger.info(
                    f"비디오 {video_id}에 대해 {len(restaurant_data)}개의 식당 정보 발견"
                )
                s_count, e_count = save_multiple_restaurants(video_id, restaurant_data)
                success_count += s_count
                error_count += e_count
                if e_count > 0:
                    problem_videos.append(video_id)
            else:
                # 단일 식당 정보인 경우
                if save_to_db(video_id, restaurant_data):
                    success_count += 1
                else:
                    error_count += 1
                    problem_videos.append(video_id)

    else:
        logger.error(f"지원되지 않는 데이터 형식: {type(restaurants_data)}")
        return

    logger.info(f"작업 완료: {success_count}개 성공, {error_count}개 실패")

    # 문제 비디오 목록 출력
    if problem_videos:
        logger.warning(f"문제가 있는 비디오 목록 ({len(problem_videos)}개):")
        for video_id in problem_videos:
            logger.warning(f" - {video_id}")

    # 저장된 데이터 조회 (테스트용)
    query_db()


if __name__ == "__main__":
    main()
