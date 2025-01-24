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



# 以下からは取得したDBを用いて分析および可視化を行う
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

class HotelReviewAnalyzer:
    def __init__(self, db_name='hotel_reviews.db'):
        self.db_name = db_name
        self.engine = create_engine(f'sqlite:///{db_name}')
    
    def fetch_data(self):
        # データベースからデータを取得
        query = """
        SELECT 
            age,
            room_ratings,
            bath_ratings,
            breakfast_ratings,
            dinner_ratings,
            service_ratings,
            cleanliness_ratings
        FROM reviews
        """
        df = pd.read_sql(query, self.engine)
        
        # 年齢を数値型に変換
        if df['age'].dtype == 'object':  # ageが文字列型の場合
            df['age'] = (
                df['age']
                .str.replace('代', '', regex=False)  # "代"を削除
                .str.strip()  # 前後の空白を削除
                .replace('', None)  # 空文字をNoneに変換
                .astype(float, errors='ignore')  # 数値型に変換
            )
        
        # 評価を数値型に変換し、欠損値を除外
        numeric_columns = ['room_ratings', 'bath_ratings', 'breakfast_ratings',
                           'dinner_ratings', 'service_ratings', 'cleanliness_ratings']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df.dropna(subset=['age'] + numeric_columns)  # 欠損値を削除

    def calculate_generation_means(self, df):
        # 総合評価の計算（各項目の平均）
        df['overall_rating'] = df[['room_ratings', 'bath_ratings', 'breakfast_ratings',
                                   'dinner_ratings', 'service_ratings', 'cleanliness_ratings']].mean(axis=1)
        
        # 世代ごとにグループ分け（例: 20代, 30代）
        df['generation'] = (df['age'] // 10 * 10).astype(int)  # 10の位で世代を計算
        
        # 世代ごとの平均評価と母数を計算
        grouped = df.groupby('generation').agg(['mean', 'count'])
        return grouped

    def display_table(self, grouped):
        # 平均値と母数を整形して表として表示
        table = grouped.reset_index()
        table.columns = ['Generation'] + [
            f'{col[0]}_{col[1]}' for col in grouped.columns
        ]
        print("\n=== 世代ごとの平均評価と母数 ===")
        print(table.to_string(index=False))
        return table

    def plot_generation_means(self, grouped):
        # 評価カテゴリのリスト
        categories = ['room_ratings', 'bath_ratings', 'breakfast_ratings',
                      'dinner_ratings', 'service_ratings', 'cleanliness_ratings', 'overall_rating']
        
        # 平均点を抽出
        mean_values = grouped[[col for col in categories]].xs('mean', axis=1, level=1)
        
        # 各世代の母数（人数）
        counts = grouped['overall_rating']['count']
        
        # 世代ごとの平均評価を棒グラフで可視化
        ax = mean_values.plot(kind='bar', figsize=(14, 7), colormap='viridis', edgecolor='black')
        plt.title('Average Ratings by Generation with Sample Size')
        plt.ylabel('Rating (1-5)')
        plt.xlabel('Generation')
        plt.xticks(rotation=0)
        plt.ylim(0, 5)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 母数を各バーの上に表示
        for idx, gen in enumerate(mean_values.index):
            plt.text(idx, 5.1, f'n={counts[gen]}', ha='center', fontsize=10, color='black')
        
        plt.legend(title='Categories', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.show()

# 使用例
analyzer = HotelReviewAnalyzer()

# データ取得
review_data = analyzer.fetch_data()

# 世代ごとの平均を計算
generation_means = analyzer.calculate_generation_means(review_data)

# 表の表示
table = analyzer.display_table(generation_means)

# 可視化
analyzer.plot_generation_means(generation_means)