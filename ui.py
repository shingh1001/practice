"""
순천시 관광 최적 동선 시각화 시스템 - 웹 대시보드
실행 방법: streamlit run ui.py
"""

import streamlit as st
import folium
from streamlit_folium import folium_static
import json
import csv
import requests
import base64
import os

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="순천시 관광 최적 동선 시각화 시스템",
    page_icon="🗺️",
    layout="wide"
)

# 카카오 API 키


# ============================================================
# 1. 거리/시간 행렬 로드
# ============================================================
@st.cache_data
def load_matrix(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["spot_ids"], data["spot_names"], data["matrix"]

# ============================================================
# 2. 관광지 데이터 로드
# ============================================================
@st.cache_data
def load_spots(csv_path):
    spots = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            spots.append({
                "id":          row["id"],
                "name":        row["name"],
                "category":    row["category"],
                "lat":         float(row["latitude"]),
                "lng":         float(row["longitude"]),
                "stay_hours":  float(row["stay_hours"]),
                "description": row.get("description", ""),
            })
    return spots

# ============================================================
# 3. images 폴더에서 관광지 사진 불러오기 (base64 변환)
# ============================================================
@st.cache_data
def get_local_image(spot_id):
    # images 폴더에서 T01.png 형태로 찾기
    path = os.path.join("images", f"{spot_id}.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    return ""

# ============================================================
# 4. 카카오 API로 실제 도로 좌표 가져오기
# ============================================================
def get_road_coords(origin_lat, origin_lng, dest_lat, dest_lng):
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
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
                coords = []
                for section in route.get("sections", []):
                    for road in section.get("roads", []):
                        vertexes = road.get("vertexes", [])
                        for i in range(0, len(vertexes) - 1, 2):
                            coords.append([vertexes[i + 1], vertexes[i]])
                return coords
    except Exception as e:
        print(f"  [에러] 도로 좌표 조회 실패: {e}")
    return []

# ============================================================
# 5. 관광지 팝업 HTML 만들기
# ============================================================
def make_popup_html(spot, entry=None, number=None):
    image_url   = get_local_image(spot["id"])
    description = spot.get("description", "")

    if number is not None:
        title = f"{number}. {spot['name']}"
    else:
        title = spot["name"]

    time_info = ""
    if entry is not None:
        time_info = (
            f"관람: {entry['arrival']} ~ {entry['departure']}<br>"
            f"이동: {entry['drive_km']}km (약 {entry['drive_min']}분)<br>"
            f"체류: 약 {entry['stay_hours']}시간<br>"
            f"<hr style='margin:4px 0'>"
        )

    if image_url:
        img_tag = f"<img src='{image_url}' width='210px' style='border-radius:6px; margin-bottom:6px;'><br>"
        width = "220px"
    else:
        img_tag = ""
        width = "200px"

    html = (
        f"<div style='width:{width}'>"
        f"{img_tag}"
        f"<b>{title}</b><br>"
        f"<hr style='margin:4px 0'>"
        f"{time_info}"
        f"<small>{description}</small>"
        f"</div>"
    )
    return html

# ============================================================
# 6. Held-Karp 알고리즘
# ============================================================
def held_karp(dist, start, targets, end=None):
    # start : 출발지 인덱스
    # targets : 방문할 관광지 인덱스 목록
    # end : 도착지 인덱스 (None이면 자동으로 최적 위치에서 종료)
    n = len(targets)
    INF = float("inf")

    dp = [[INF] * n for _ in range(1 << n)]
    parent = [[-1] * n for _ in range(1 << n)]

    for i in range(n):
        dp[1 << i][i] = dist[start][targets[i]]

    for visited in range(1, 1 << n):
        for curr in range(n):
            if not (visited & (1 << curr)):
                continue
            if dp[visited][curr] == INF:
                continue
            for next_node in range(n):
                if visited & (1 << next_node):
                    continue
                new_visited = visited | (1 << next_node)
                new_cost = dp[visited][curr] + dist[targets[curr]][targets[next_node]]
                if new_cost < dp[new_visited][next_node]:
                    dp[new_visited][next_node] = new_cost
                    parent[new_visited][next_node] = curr

    full_visited = (1 << n) - 1
    best_cost = INF
    last_node = -1

    if end is not None and end in targets:
        # 도착지가 관광지 중 하나로 고정된 경우
        end_pos = targets.index(end)
        best_cost = dp[full_visited][end_pos]
        last_node = end_pos
    elif end is not None:
        # 도착지가 관광지가 아닌 별도 장소(출발지 목록 등)인 경우
        # 마지막 관광지에서 도착지까지 거리를 더해서 최소 찾기
        for i in range(n):
            total = dp[full_visited][i] + dist[targets[i]][end]
            if total < best_cost:
                best_cost = total
                last_node = i
    else:
        # 도착지 지정 안 함 (자동)
        for i in range(n):
            if dp[full_visited][i] < best_cost:
                best_cost = dp[full_visited][i]
                last_node = i

    path_indices = []
    visited = full_visited
    curr = last_node
    while curr != -1:
        path_indices.append(curr)
        prev = parent[visited][curr]
        visited = visited ^ (1 << curr)
        curr = prev
    path_indices.reverse()

    best_path = [start] + [targets[i] for i in path_indices]

    # 도착지가 별도 장소면 경로 끝에 추가
    if end is not None and end not in targets:
        best_path.append(end)

    return best_cost, best_path

# ============================================================
# 7. 시간 포맷
# ============================================================
def format_time(minutes):
    if minutes >= 1440:
        minutes = minutes - 1440
        h = int(minutes // 60)
        m = int(minutes % 60)
        return f"다음날 {h:02d}:{m:02d}"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h:02d}:{m:02d}"

# ============================================================
# 8. 타임테이블 생성
# ============================================================
def build_timetable(path, dist_matrix, dur_matrix, spots, start_hour):
    timetable = []
    current_minutes = start_hour * 60
    total_distance = 0
    total_drive_time = 0

    for step, idx in enumerate(path):
        spot = spots[idx]
        entry = {"step": step + 1, "name": spot["name"]}

        if step == 0:
            entry["arrival"]    = format_time(current_minutes)
            entry["departure"]  = format_time(current_minutes)
            entry["drive_km"]   = 0
            entry["drive_min"]  = 0
            entry["stay_hours"] = 0
        else:
            prev_idx   = path[step - 1]
            drive_dist = dist_matrix[prev_idx][idx]
            drive_dur  = dur_matrix[prev_idx][idx]
            drive_min  = drive_dur / 60

            total_distance   += drive_dist
            total_drive_time += drive_dur

            arrival   = current_minutes + drive_min
            departure = arrival + (spot["stay_hours"] * 60)

            entry["arrival"]    = format_time(arrival)
            entry["departure"]  = format_time(departure)
            entry["drive_km"]   = round(drive_dist / 1000, 1)
            entry["drive_min"]  = round(drive_min)
            entry["stay_hours"] = spot["stay_hours"]

            current_minutes = departure

        timetable.append(entry)

    summary = {
        "total_distance_km": round(total_distance / 1000, 1),
        "total_drive_min":   round(total_drive_time / 60),
        "end_time":          format_time(current_minutes),
        "start_time":        format_time(start_hour * 60),
    }

    return timetable, summary

# ============================================================
# 9. 지도 생성
# ============================================================
def create_map(spots, path=None, timetable=None, road_coords_list=None, highlight_segment=None, end_idx=None):
    m = folium.Map(location=[34.95, 127.44], zoom_start=12)

    if path and timetable:
        # 경로 선 그리기
        for i in range(len(path) - 1):
            from_idx = path[i]
            to_idx   = path[i + 1]

            if road_coords_list and i < len(road_coords_list) and road_coords_list[i]:
                coords = road_coords_list[i]
            else:
                coords = [
                    [spots[from_idx]["lat"], spots[from_idx]["lng"]],
                    [spots[to_idx]["lat"],   spots[to_idx]["lng"]],
                ]

            if highlight_segment is not None and i == highlight_segment:
                color, weight, opacity = "red", 6, 0.9
            elif highlight_segment is not None:
                color, weight, opacity = "gray", 2, 0.25
            else:
                color, weight, opacity = "blue", 4, 0.7

            folium.PolyLine(coords, weight=weight, color=color, opacity=opacity).add_to(m)

        # 마커 찍기
        marker_num = 0
        for i, entry in enumerate(timetable):
            idx  = path[i]
            spot = spots[idx]

            if i == 0:
                folium.Marker(
                    location=[spot["lat"], spot["lng"]],
                    popup=folium.Popup(f"<b>🚩 출발지: {spot['name']}</b>", max_width=200),
                    tooltip=f"🚩 출발지: {spot['name']}",
                    icon=folium.Icon(color="red", icon="star", prefix="fa")
                ).add_to(m)
            elif spot["id"].startswith("S"):
                # 도착지가 출발지 목록(순천역 등)인 경우
                folium.Marker(
                    location=[spot["lat"], spot["lng"]],
                    popup=folium.Popup(f"<b>🏁 도착지: {spot['name']}</b>", max_width=200),
                    tooltip=f"🏁 도착지: {spot['name']}",
                    icon=folium.Icon(color="green", icon="flag", prefix="fa")
                ).add_to(m)
            else:
                marker_num += 1
                popup_html = make_popup_html(spot, entry, number=marker_num)

                # 도착지로 선택된 관광지면 초록색, 아니면 파란색
                if end_idx is not None and idx == end_idx:
                    bg_color = "#16A34A"   # 초록색 (도착지)
                    tip = f"🏁 {marker_num}. {spot['name']} (도착지)"
                else:
                    bg_color = "#3B82F6"   # 파란색 (일반)
                    tip = f"{marker_num}. {spot['name']}"

                div_icon = folium.DivIcon(
                    html=f"""
                        <div style="
                            background-color: {bg_color};
                            color: white;
                            border-radius: 50%;
                            width: 28px;
                            height: 28px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: bold;
                            font-size: 13px;
                            border: 2px solid white;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                        ">{marker_num}</div>
                    """,
                    icon_size=(28, 28),
                    icon_anchor=(14, 14),
                )

                folium.Marker(
                    location=[spot["lat"], spot["lng"]],
                    popup=folium.Popup(popup_html, max_width=230),
                    tooltip=tip,
                    icon=div_icon
                ).add_to(m)

        lats = [spots[i]["lat"] for i in path]
        lngs = [spots[i]["lng"] for i in path]
        m.fit_bounds([
            [min(lats) - 0.01, min(lngs) - 0.01],
            [max(lats) + 0.01, max(lngs) + 0.01]
        ])

    else:
        # 초기 상태: 모든 장소 마커 (관광지는 사진 + 설명 팝업)
        for spot in spots:
            if spot["id"].startswith("S"):
                folium.Marker(
                    location=[spot["lat"], spot["lng"]],
                    popup=folium.Popup(f"<b>🚩 출발지: {spot['name']}</b>", max_width=200),
                    tooltip=f"🚩 출발지: {spot['name']}",
                    icon=folium.Icon(color="red", icon="star", prefix="fa")
                ).add_to(m)
            else:
                popup_html = make_popup_html(spot)
                folium.Marker(
                    location=[spot["lat"], spot["lng"]],
                    popup=folium.Popup(popup_html, max_width=230),
                    tooltip=spot["name"],
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)

    return m

# ============================================================
# 메인 앱
# ============================================================
def main():

    try:
        spot_ids, spot_names, dist_matrix = load_matrix("distance_matrix.json")
        spot_ids, spot_names, dur_matrix  = load_matrix("duration_matrix.json")
        spots                              = load_spots("suncheon_spots.csv")
    except FileNotFoundError:
        st.error("데이터 파일을 찾을 수 없습니다. build_distance_matrix.py를 먼저 실행하세요.")
        return

    st.title("🗺️ 순천시 관광 최적 동선 시각화 시스템")

    with st.sidebar:
        st.header("여행 설정")

        st.subheader("📍 출발지")
        start_options = {}
        for i, spot in enumerate(spots):
            if spot["id"].startswith("S"):
                start_options[spot["name"]] = i
        start_name = st.selectbox("출발지를 선택하세요", list(start_options.keys()))
        start_idx = start_options[start_name]

        st.subheader("⏰ 출발 시간")
        start_hour = st.slider("출발 시각", min_value=6, max_value=12, value=9)
        st.write(f"**{start_hour}:00** 출발")

        # 도착지 선택
        st.subheader("🏁 도착지")
        end_options = {"지정 안 함 (자동)": None}
        # 출발지 목록 추가
        for i, spot in enumerate(spots):
            if spot["id"].startswith("S"):
                end_options[f"{spot['name']} (출발지)"] = i
        # 관광지 목록 추가
        for i, spot in enumerate(spots):
            if spot["id"].startswith("T"):
                end_options[spot["name"]] = i
        end_name = st.selectbox("도착지를 선택하세요", list(end_options.keys()))
        end_idx = end_options[end_name]

        highlight_segment = None
        if "result" in st.session_state:
            st.subheader("🔍 구간 선택")
            result    = st.session_state["result"]
            best_path = result["best_path"]

            segment_options = ["전체 보기"]
            for i in range(len(best_path) - 1):
                from_name = spots[best_path[i]]["name"]
                to_name   = spots[best_path[i + 1]]["name"]
                segment_options.append(f"{i + 1}구간: {from_name} → {to_name}")

            selected_segment = st.selectbox("구간을 선택하면 지도에 강조 표시됩니다", segment_options)
            if selected_segment != "전체 보기":
                highlight_segment = int(selected_segment.split("구간")[0]) - 1

        st.subheader("🏛️ 관광지 선택")

        col1, col2 = st.columns(2)
        with col1:
            select_all = st.button("전체 선택", use_container_width=True)
        with col2:
            deselect_all = st.button("전체 삭제", use_container_width=True)

        if select_all:
            st.session_state["select_all"] = True
        if deselect_all:
            st.session_state["select_all"] = False

        default_value = st.session_state.get("select_all", False)

        selected_indices = []
        for i, spot in enumerate(spots):
            if spot["id"].startswith("T"):
                checked = st.checkbox(
                    f"{spot['name']} (약 {spot['stay_hours']}시간)",
                    value=default_value,
                    key=f"spot_{i}_{default_value}"
                )
                if checked:
                    selected_indices.append(i)

        st.divider()
        st.write(f"선택된 관광지: **{len(selected_indices)}곳**")

        search_button = st.button(
            "🔍 최적 경로 탐색",
            type="primary",
            use_container_width=True,
            disabled=len(selected_indices) == 0
        )

    if search_button and len(selected_indices) > 0:
        with st.spinner("최적 경로를 계산 중입니다..."):
            best_cost, best_path = held_karp(dist_matrix, start_idx, selected_indices, end_idx)

        timetable, summary = build_timetable(best_path, dist_matrix, dur_matrix, spots, start_hour)

        road_coords_list = []
        with st.spinner("실제 도로 경로를 불러오는 중입니다..."):
            for i in range(len(best_path) - 1):
                from_spot = spots[best_path[i]]
                to_spot   = spots[best_path[i + 1]]
                coords = get_road_coords(
                    from_spot["lat"], from_spot["lng"],
                    to_spot["lat"],   to_spot["lng"]
                )
                road_coords_list.append(coords)

        st.session_state["result"] = {
            "best_path":        best_path,
            "timetable":        timetable,
            "summary":          summary,
            "road_coords_list": road_coords_list,
            "end_idx":          end_idx,
        }
        st.rerun()

    if "result" in st.session_state:
        result           = st.session_state["result"]
        best_path        = result["best_path"]
        timetable        = result["timetable"]
        summary          = result["summary"]
        road_coords_list = result.get("road_coords_list", [])
        end_idx          = result.get("end_idx", None)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 이동 거리", f"{summary['total_distance_km']} km")
        with col2:
            h = summary["total_drive_min"] // 60
            m = summary["total_drive_min"] % 60
            st.metric("총 주행 시간", f"약 {h}시간 {m}분")
        with col3:
            total_stay = 0
            for idx in best_path[1:]:
                total_stay += spots[idx]["stay_hours"]
            st.metric("총 체류 시간", f"약 {total_stay}시간")
        with col4:
            st.metric("여행 종료", summary["end_time"])

        st.subheader("🗺️ 최적 경로 지도")
        route_map = create_map(spots, best_path, timetable, road_coords_list, highlight_segment, end_idx)
        folium_static(route_map, width=1100, height=500)

        st.subheader("📋 타임테이블")
        tourist_count = 0
        for i, entry in enumerate(timetable):
            spot_idx = best_path[i]
            spot = spots[spot_idx]

            if i == 0:
                # 출발지
                st.write(f"🚩 **{entry['name']}** | 출발 {entry['departure']}")
            elif spot["id"].startswith("S"):
                # 도착지 (출발지 목록에서 선택된 경우)
                st.write(f"↓ 이동 {entry['drive_km']}km (약 {entry['drive_min']}분)")
                st.write(f"🏁 **{entry['name']}** | 도착 {entry['arrival']}")
            else:
                # 관광지
                tourist_count += 1
                st.write(f"↓ 이동 {entry['drive_km']}km (약 {entry['drive_min']}분)")
                img_col, txt_col = st.columns([1, 3])
                with img_col:
                    img_path = os.path.join("images", f"{spot['id']}.png")
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                with txt_col:
                    st.write(
                        f"**{tourist_count}. {entry['name']}**  \n"
                        f"관람 {entry['arrival']} ~ {entry['departure']}  \n"
                        f"체류 약 {entry['stay_hours']}시간"
                    )
            st.divider()

        st.subheader("📌 방문 순서")
        route_names = []
        for idx in best_path:
            route_names.append(spots[idx]["name"])
        st.write(" → ".join(route_names))

    else:
        st.info("왼쪽 사이드바에서 출발지와 관광지를 선택한 후 '최적 경로 탐색' 버튼을 눌러주세요. 지도의 관광지 마커를 클릭하면 사진과 설명을 볼 수 있습니다.")
        init_map = create_map(spots)
        folium_static(init_map, width=1100, height=500)

if __name__ == "__main__":
    main()