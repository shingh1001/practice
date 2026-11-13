"""
순천 여행 플래너 - 거리 행렬 수집 스크립트 (도로 좌표 포함)
카카오 모빌리티 API를 이용하여 17개 장소 간 실제 주행 거리/시간/도로좌표를 수집합니다.

사용법: python build_distance_matrix.py
결과물: distance_matrix.json, duration_matrix.json, route_coords.json
"""

import requests
import json
import time
import csv
import os

# ============================================================
# 설정
# ============================================================
KAKAO_REST_API_KEY = "7a66fb10317005d8ac4f526317f59190"
CSV_FILE = "suncheon_spots.csv"
OUTPUT_DISTANCE = "distance_matrix.json"
OUTPUT_DURATION = "duration_matrix.json"
OUTPUT_COORDS   = "route_coords.json"
API_DELAY = 0.2

# ============================================================
# 1. CSV에서 장소 데이터 로드
# ============================================================
def load_spots(csv_path):
    spots = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            spots.append({
                "id":  row["id"],
                "name": row["name"],
                "lat": float(row["latitude"]),
                "lng": float(row["longitude"]),
            })
    return spots

# ============================================================
# 2. 카카오 모빌리티 API 호출 (도로 좌표 포함)
# ============================================================
def get_driving_info(origin_lng, origin_lat, dest_lng, dest_lat):
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }
    params = {
        "origin":      f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "priority":    "RECOMMEND",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()

        if resp.status_code == 200 and data.get("routes"):
            route = data["routes"][0]
            if route["result_code"] == 0:
                summary  = route["summary"]
                distance = summary["distance"]   # 미터
                duration = summary["duration"]   # 초

                # 도로 좌표 추출
                coords = []
                sections = route.get("sections", [])
                for section in sections:
                    roads = section.get("roads", [])
                    for road in roads:
                        vertexes = road.get("vertexes", [])
                        # vertexes는 [경도, 위도, 경도, 위도, ...] 형태
                        for i in range(0, len(vertexes) - 1, 2):
                            lng = vertexes[i]
                            lat = vertexes[i + 1]
                            coords.append([lat, lng])  # folium은 [위도, 경도] 순서

                return distance, duration, coords

        print(f"  [경고] API 응답 이상: status={resp.status_code}")
        return None, None, []

    except Exception as e:
        print(f"  [에러] {e}")
        return None, None, []

# ============================================================
# 3. 전체 행렬 구축
# ============================================================
def build_matrix(spots):
    n = len(spots)
    dist_matrix   = [[0] * n for _ in range(n)]
    dur_matrix    = [[0] * n for _ in range(n)]
    # route_coords[i][j] = i번 장소에서 j번 장소까지의 도로 좌표 리스트
    route_coords  = [[[] for _ in range(n)] for _ in range(n)]

    total_calls = n * (n - 1)
    current = 0
    failed  = 0

    print(f"\n총 {n}개 장소, API 호출 {total_calls}회 예정\n")
    print("=" * 60)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            current += 1
            print(f"[{current}/{total_calls}] {spots[i]['name']} -> {spots[j]['name']} ... ", end="")

            distance, duration, coords = get_driving_info(
                spots[i]["lng"], spots[i]["lat"],
                spots[j]["lng"], spots[j]["lat"]
            )

            if distance is not None:
                dist_matrix[i][j]  = distance
                dur_matrix[i][j]   = duration
                route_coords[i][j] = coords
                print(f"{distance/1000:.1f}km, {duration/60:.0f}분, 좌표 {len(coords)}개")
            else:
                failed += 1
                print("실패!")

            time.sleep(API_DELAY)

    print("=" * 60)
    print(f"\n완료! 성공: {total_calls - failed}, 실패: {failed}")

    return dist_matrix, dur_matrix, route_coords

# ============================================================
# 4. 결과 저장
# ============================================================
def save_results(spots, dist_matrix, dur_matrix, route_coords):
    names = [s["name"] for s in spots]
    ids   = [s["id"]   for s in spots]

    dist_data = {
        "spot_ids":   ids,
        "spot_names": names,
        "unit":       "meters",
        "matrix":     dist_matrix
    }

    dur_data = {
        "spot_ids":   ids,
        "spot_names": names,
        "unit":       "seconds",
        "matrix":     dur_matrix
    }

    coords_data = {
        "spot_ids":   ids,
        "spot_names": names,
        "coords":     route_coords
    }

    with open(OUTPUT_DISTANCE, "w", encoding="utf-8") as f:
        json.dump(dist_data, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DURATION, "w", encoding="utf-8") as f:
        json.dump(dur_data, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_COORDS, "w", encoding="utf-8") as f:
        json.dump(coords_data, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료:")
    print(f"  - 거리 행렬: {OUTPUT_DISTANCE}")
    print(f"  - 시간 행렬: {OUTPUT_DURATION}")
    print(f"  - 도로 좌표: {OUTPUT_COORDS}")

# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  순천 여행 플래너 - 거리 행렬 수집기 (도로 좌표 포함)")
    print("=" * 60)

    if not os.path.exists(CSV_FILE):
        print(f"\n[에러] {CSV_FILE} 파일을 찾을 수 없습니다.")
        exit(1)

    spots = load_spots(CSV_FILE)
    print(f"\n{len(spots)}개 장소 로드 완료")

    dist_matrix, dur_matrix, route_coords = build_matrix(spots)
    save_results(spots, dist_matrix, dur_matrix, route_coords)

    print("\n다음 단계: ui.py를 실행하세요!")