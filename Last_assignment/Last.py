from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
import time
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.types import Integer

# ホテルのクチコミ情報をスクレイピングするクラス
class HotelReviewScraper:
    def __init__(self, url_list):
        self.url_list = url_list
        self.data = {
            'sex': [],
            'age': [],
            'purpose': [],
            'room_type': [],
            'meal_type': [],
            'post_date': [],
            'periods': [],
            'plans': [],
            'prices': [],
            'room_ratings': [],
            'bath_ratings': [],
            'breakfast_ratings': [],
            'dinner_ratings': [],
            'service_ratings': [],
            'cleanliness_ratings': [],
            'hotel_name': []
        }

    # クチコミ情報を取得
    def fetch_reviews(self):
        for url in self.url_list:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            self._extract_review_data(soup)
            time.sleep(2)  # 2秒待機

    # クチコミ情報を抽出
    def _extract_review_data(self, soup):
        self._extract_labels(soup)
        self._extract_post_dates(soup)
        self._extract_plan_info(soup)
        self._extract_ratings(soup)
        self._extract_hotel_name(soup)

    # クチコミ情報からラベル情報を抽出
    def _extract_labels(self, soup):
        c_label = soup.find_all("span", class_='c-label')
        for item in c_label:
            text = item.get_text(strip=True)
            if '代' in text:
                sex_age = text.split('/')
                if len(sex_age) == 2:
                    self.data['sex'].append(sex_age[0])
                    self.data['age'].append(re.sub(r'[^\d]', '', sex_age[1]))  
                else:
                    self.data['sex'].append(None)
                    self.data['age'].append(None)
            elif '旅行' in text or '出張' in text:
                self.data['purpose'].append(text)
            elif 'ツイン' in text or 'シングル' in text or '和室' in text:
                self.data['room_type'].append(text)
            elif '朝・夕' in text or '朝食' in text or '夕食' in text:
                self.data['meal_type'].append(text)

    # クチコミ情報から投稿日を抽出
    def _extract_post_dates(self, soup):
        post_date = soup.find_all("p", class_='jlnpc-kuchikomiCassette__postDate')
        for text in post_date:
            date_pattern = r'\d{4}/\d{1,2}/\d{1,2}'
            match = re.search(date_pattern, text.get_text())
            if match:
                self.data['post_date'].append(match.group())

    # クチコミ情報からプラン情報を抽出
    def _extract_plan_info(self, soup):
        plan_info = soup.find_all("dl", class_='jlnpc-kuchikomiCassette__planInfoList')
        for item in plan_info:
            dt_text = item.find('dt').get_text(strip=True)
            dd_text = item.find('dd').get_text(strip=True)
            if dt_text == '時期':
                self.data['periods'].append(dd_text)
            elif dt_text == 'プラン':
                self.data['plans'].append(dd_text)
            elif dt_text == '価格帯':
                self.data['prices'].append(dd_text.split('（')[0].strip())

    # クチコミ情報から評価情報を抽出
    def _extract_ratings(self, soup):
        rate_list = soup.find_all("dl", class_='jlnpc-kuchikomiCassette__rateList')
        for item in rate_list:
            categories = item.find_all('dt')
            ratings = item.find_all('dd')
            for category, rating in zip(categories, ratings):
                category_text = category.get_text(strip=True)
                rating_text = self._convert_rating_to_int(rating.get_text(strip=True))
                if '部屋' in category_text:
                    self.data['room_ratings'].append(rating_text)
                elif '風呂' in category_text:
                    self.data['bath_ratings'].append(rating_text)
                elif '料理(朝食)' in category_text:
                    self.data['breakfast_ratings'].append(rating_text)
                elif '料理(夕食)' in category_text:
                    self.data['dinner_ratings'].append(rating_text)
                elif '接客・サービス' in category_text:
                    self.data['service_ratings'].append(rating_text)
                elif '清潔感' in category_text:
                    self.data['cleanliness_ratings'].append(rating_text)

    # 評価情報を整数に変換
    def _convert_rating_to_int(self, rating_text):
        try:
            return int(rating_text)
        except ValueError:
            return None

    # クチコミ情報からホテル名を抽出
    def _extract_hotel_name(self, soup):
        hotel_name_text = soup.find_all("p", class_='jlnpc-styleguide-scope jlnpc-yado__subTitle')
        hotel_names = [name.get_text(strip=True).split('のクチコミ・評価')[0] for name in hotel_name_text]
        self.data['hotel_name'].extend(hotel_names * len(self.data['sex']))

    # データフレームを取得
    def get_dataframe(self):
        max_length = max(len(lst) for lst in self.data.values())
        for key in self.data:
            self.data[key] = self._pad_list(self.data[key], max_length)
        return pd.DataFrame(self.data)

    # リストを指定の長さにパディング
    def _pad_list(self, lst, length, fill_value=None):
        return lst + [fill_value] * (length - len(lst))

    # データベースに保存
    def save_to_db(self, db_name='hotel_reviews.db'):
        df = self.get_dataframe()
        df = df.where(pd.notnull(df), None)
        engine = create_engine(f'sqlite:///{db_name}')
        df.to_sql(
            'reviews',
            con=engine,
            if_exists='replace',
            index=False,
            dtype={
                'age': Integer,
                'room_ratings': Integer,
                'bath_ratings': Integer,
                'breakfast_ratings': Integer,
                'dinner_ratings': Integer,
                'service_ratings': Integer,
                'cleanliness_ratings': Integer
            }
        )
        print(f'Data saved to {db_name}')

# クチコミ情報を取得するURLリスト
url_list = ['https://www.jalan.net/yad309590/kuchikomi/']
scraper = HotelReviewScraper(url_list)
scraper.fetch_reviews()
scraper.save_to_db()
