import flet as ft
import requests
import json

# ローカルの天気アイコンデータを格納したJSONファイルのパス
WEATHER_ICONS_JSON_PATH = "/Users/chihiro/dsprog2/dsprog2/jma/weather_codes.json"  # ローカルJSONファイルのパス

# ローカルJSONファイルからアイコンの情報を読み込む
def load_weather_icons(json_path):
    """ローカルJSONファイルから天気アイコンデータを読み取る"""
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading weather icons JSON file: {e}")
        return None

# 天気予報APIのURL（地域コードを使ってデータを取得）
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"

def fetch_weather_data(area_code):
    """指定された地域コードの天気予報を取得"""
    try:
        url = FORECAST_URL.format(code=area_code)
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def load_area_list(json_path):
    """ローカルJSONファイルから地域データを読み取る"""
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None

def main(page: ft.Page):
    page.title = "一週間の天気予報"

    # 地域データを読み込む
    area_list = load_area_list("/Users/chihiro/dsprog2/dsprog2/jma/weather.json")
    if not area_list:
        page.add(ft.Text("地域データの読み込みに失敗しました。"))
        return

    # 天気アイコンデータを読み込む
    weather_icons = load_weather_icons(WEATHER_ICONS_JSON_PATH)
    if not weather_icons:
        page.add(ft.Text("天気アイコンの読み込みに失敗しました。"))
        return

    # UI要素
    center_dropdown = ft.Dropdown(label="地方を選択してください", options=[], on_change=lambda e: update_areas(e))
    area_dropdown = ft.Dropdown(label="地域を選択してください", options=[], on_change=lambda e: update_weather(e))
    weather_output = ft.ListView(expand=True)

    # 地方選択時
    def update_areas(e):
        center_code = center_dropdown.value
        selected_center = area_list["centers"].get(center_code, None)

        if selected_center:
            area_dropdown.options = [
                ft.dropdown.Option(child) for child in selected_center["children"]
            ]
            area_dropdown.value = None
            area_dropdown.disabled = False
        else:
            area_dropdown.options = []
            area_dropdown.disabled = True
        page.update()

    # 地域選択時
    def update_weather(e):
        area_code = area_dropdown.value
        weather_output.controls.clear()  # 表示をクリア
        if area_code:
            weather_data = fetch_weather_data(area_code)
            if weather_data:
                try:
                    # JSONデータから天気予報の詳細を抽出
                    for data in weather_data:
                        time_series = data.get("timeSeries", [])
                        for time_data in time_series:
                            areas = time_data.get("areas", [])
                            for area in areas:
                                if area["area"]["code"] == area_code:
                                    weather_output.controls.append(
                                        ft.Text(f"地域: {area['area']['name']}", size=20, weight=ft.FontWeight.BOLD)
                                    )
                                    # 天気アイコンの表示
                                    for i, weather in enumerate(area.get("weathers", [])):
                                        weather_code = area.get("weatherCodes", [])[i]  # 天気コード取得
                                        icon_filename = weather_icons.get(str(weather_code), [None])[0]  # アイコンファイル名取得
                                        if icon_filename:
                                            icon_url = f"https://www.jma.go.jp/bosai/forecast/img/{icon_filename}"
                                            weather_output.controls.append(
                                                ft.Image(src=icon_url, width=50, height=50)  # アイコンの表示
                                            )
                                        weather_output.controls.append(
                                            ft.Text(f"{i+1}日目の天気: {weather}")
                                        )
                                    # 降水確率
                                    for i, pop in enumerate(area.get("pops", [])):
                                        weather_output.controls.append(
                                            ft.Text(f"{i+1}日目の降水確率: {pop or 'データなし'}%")
                                        )
                                    # 気温
                                    for i, temp in enumerate(area.get("temps", [])):
                                        weather_output.controls.append(
                                            ft.Text(f"{i+1}日目の気温: {temp or 'データなし'}℃")
                                        )
                                    break
                except KeyError as ex:
                    weather_output.controls.append(ft.Text("天気データが見つかりません。"))
                    print(f"KeyError: {ex}")
            else:
                weather_output.controls.append(ft.Text("天気データの取得に失敗しました。"))
        else:
            weather_output.controls.append(ft.Text("地域を選択してください。"))
        page.update()

    # 初期化
    center_dropdown.options = [
        ft.dropdown.Option(code, center["name"]) for code, center in area_list["centers"].items()
    ]
    area_dropdown.disabled = True

    # ページに要素を追加
    page.add(
        ft.Column(
            [
                center_dropdown,
                area_dropdown,
                ft.Divider(),
                ft.Text("一週間の天気予報", size=24, weight=ft.FontWeight.BOLD),
                weather_output,
            ],
            alignment=ft.MainAxisAlignment.START,
            expand=True,
        )
    )


ft.app(main)
