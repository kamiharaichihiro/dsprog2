import flet as ft
import requests
import json
import sqlite3

WEATHER_ICONS_JSON_PATH = "/Users/chihiro/DS-Prog2/jma/weather_codes.json" 

def create_db():
    """SQLiteデータベースとテーブルを作成"""
    conn = sqlite3.connect('weather_forecast.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_code TEXT,
            forecast_date TEXT,
            weather TEXT,
            temp_max INTEGER,
            temp_min INTEGER,
            pop INTEGER,
            icon_filename TEXT
        )
    ''')
    conn.commit()
    conn.close()

def load_weather_icons(json_path):
    """ローカルJSONファイルから天気アイコンデータを読み取る"""
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading weather icons JSON file: {e}")
        return {}

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
        return {}

def save_weather_data_to_db(area_code, weather_data, weather_icons):
    """天気予報データをデータベースに保存"""
    conn = sqlite3.connect('weather_forecast.db')
    c = conn.cursor()
    
    for data in weather_data:
        time_series = data.get("timeSeries", [])
        for time_data in time_series:
            areas = time_data.get("areas", [])
            for area in areas:
                if area["area"]["code"] == area_code:
                    dates = time_data.get("timeDefines", [])
                    temps_max = area.get("tempsMax", [])
                    temps_min = area.get("tempsMin", [])
                    for i, date in enumerate(dates[:7]): 
                        weather_code = area.get("weatherCodes", [])[i] if i < len(area.get("weatherCodes", [])) else None
                        weather_desc = area.get("weathers", [])[i] if i < len(area.get("weathers", [])) else "天気データなし"
                        
                        icon_filename = weather_icons.get(str(weather_code), [None])[0]
                        
                        temp_max = temps_max[i] if i < len(temps_max) else "データなし"
                        temp_min = temps_min[i] if i < len(temps_min) else "データなし"
                        pop = area.get("pops", [])[i] if i < len(area.get("pops", [])) else "データなし"
                        
                        c.execute('''
                            INSERT INTO weather_forecasts (area_code, forecast_date, weather, temp_max, temp_min, pop, icon_filename)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (area_code, date, weather_desc, temp_max, temp_min, pop, icon_filename))
    
    conn.commit()
    conn.close()

def get_weather_data_from_db(area_code, selected_date=None):
    """データベースから天気予報データを取得"""
    conn = sqlite3.connect('weather_forecast.db')
    c = conn.cursor()
    if selected_date:
        c.execute('''
            SELECT * FROM weather_forecasts WHERE area_code = ? AND forecast_date = ?
        ''', (area_code, selected_date))
    else:
        c.execute('''
            SELECT * FROM weather_forecasts WHERE area_code = ?
        ''', (area_code,))
    forecasts = c.fetchall()
    conn.close()
    return forecasts

def main(page: ft.Page):
    page.title = "一週間の天気予報"

    area_list = load_area_list("/Users/chihiro/DS-Prog2/jma/weather.json")
    if not area_list:
        page.add(ft.Text("地域データの読み込みに失敗しました。"))
        return

    weather_icons = load_weather_icons(WEATHER_ICONS_JSON_PATH)
    if not weather_icons:
        page.add(ft.Text("天気アイコンの読み込みに失敗しました。"))
        return

    center_dropdown = ft.Dropdown(label="地方を選択してください", options=[], on_change=lambda e: update_areas(e))
    area_dropdown = ft.Dropdown(label="地域を選択してください", options=[], on_change=lambda e: update_weather(e))
    weather_output = ft.ListView(expand=True)

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

    def update_weather(e):
        area_code = area_dropdown.value
        weather_output.controls.clear()
        if area_code:
            weather_data = fetch_weather_data(area_code)
            if weather_data:
                save_weather_data_to_db(area_code, weather_data, weather_icons) 
                try:
                    forecast_found = False
                    weather_row = ft.Row(spacing=20) 
                    for data in weather_data:
                        time_series = data.get("timeSeries", [])
                        for time_data in time_series:
                            areas = time_data.get("areas", [])
                            for area in areas:
                                if area["area"]["code"] == area_code:
                                    forecast_found = True
                                    dates = time_data.get("timeDefines", [])
                                    temps_max = area.get("tempsMax", [])
                                    temps_min = area.get("tempsMin", [])
                                    for i, date in enumerate(dates[:7]): 
                                        formatted_date = f"{int(date[5:7])}/{int(date[8:10])}"

                                        weather_code = area.get("weatherCodes", [])[i] if i < len(area.get("weatherCodes", [])) else None
                                        weather_desc = area.get("weathers", [])[i] if i < len(area.get("weathers", [])) else "天気データなし"

                                        icon_filename = weather_icons.get(str(weather_code), [None])[0]  # アイコン名を取得
                                        icon_url = None
                                        if icon_filename:
                                            icon_url = f"https://www.jma.go.jp/bosai/forecast/img/{icon_filename}"

                                        pop = area.get("pops", [])[i] if i < len(area.get("pops", [])) else "データなし"
                                        temp_max = temps_max[i] if i < len(temps_max) else "データなし"
                                        temp_min = temps_min[i] if i < len(temps_min) else "データなし"

                                        day_info = ft.Column([
                                            ft.Text(formatted_date, size=12),
                                            ft.Text(f"{weather_desc}", size=12), 
                                            ft.Image(src=icon_url, width=50, height=50) if icon_url else ft.Text("アイコンなし"),
                                            ft.Text(f"降水確率: {pop}%", size=12),
                                            ft.Text(f"最高気温: {temp_max}℃", color=ft.colors.RED, size=12),
                                            ft.Text(f"最低気温: {temp_min}℃", color=ft.colors.BLUE, size=12)
                                        ])
                                        weather_row.controls.append(day_info)

                                    break
                        if forecast_found:
                            break

                    if forecast_found:
                        weather_output.controls.append(weather_row)
                    else:
                        weather_output.controls.append(ft.Text("指定された地域の天気データが見つかりません。"))
                except KeyError as ex:
                    weather_output.controls.append(ft.Text("天気データが正しく処理できませんでした。"))
                    print(f"KeyError: {ex}")
            else:
                weather_output.controls.append(ft.Text("天気データの取得に失敗しました。"))
        else:
            weather_output.controls.append(ft.Text("地域を選択してください。"))
        page.update()

    center_dropdown.options = [
        ft.dropdown.Option(code, center["name"]) for code, center in area_list["centers"].items()
    ]
    area_dropdown.disabled = True

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


create_db()

ft.app(main)
