from flask import Flask, render_template, request, redirect, url_for
import pymysql
import sys
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from scipy.sparse.linalg import svds
import numpy as np

db = pymysql.connect(
    user='root',
    password='DevelopJSG1!',
    host='127.0.0.1',
    db='user',
    charset='utf8'
)
cursor = db.cursor()
application = Flask(__name__)


@application.route("/")
def hello(name=None):
    return render_template('index.html', name=name)

@application.route("/signUp", methods=['GET','POST'])
def signUp():
    if request.method == 'GET':
        return render_template('signUp.html')
    else:
        userid = request.form.get('userid')
        password = request.form.get('password')
        
        sql = """
            INSERT INTO users(id, password) VALUES('%s', '%s') 
        """ % (userid, password)
        
        cursor.execute(sql)
        db.commit()
        return redirect('/')
 
@application.route("/login", methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        userid = request.form.get('userid')
        password = request.form.get('password')
        
        sql = """
            SELECT * FROM users WHERE id = '%s' and password = '%s' 
        """ % (userid, password)
        
        cursor.execute(sql)
        result = cursor.fetchall()
        print(len(result))
        if len(result) > 0:
            dataset = pd.read_csv("Music_data.csv")
            
            
            # 색인 삭제
            del dataset['Unnamed: 0']

            # 사용자 별 음악 평점을 나타내도록 테이블 변환 결측 평점은 모두 0점
            user_music_ratings = dataset.pivot_table('star_rating', index = 'customer_id', columns = 'product_title').fillna(0)

            # 피벗 테이블을 numpy의 매트릭스로 변환
            matrix = user_music_ratings.values

            # 평균 평점
            user_ratings_mean = np.mean(matrix, axis = 1)

            # 사용자별 평가 점수에 평균 평점을 뺌
            matrix_user_mean = matrix - user_ratings_mean.reshape(-1,1) 

            # SVD 기법으로 반환 값이 U, Sigma, V 전치행렬이 나옴
            U, sigma, Vt = svds(matrix_user_mean, k = 12) 

            # 0이 포함된 대칭행렬로 변환
            sigma = np.diag(sigma)


            # U, Sigma, Vt 행렬에 대한 내적 수행
            svd_user_predicted_ratings = np.dot(np.dot(U, sigma), Vt) + user_ratings_mean.reshape(-1, 1)

            # 내적 수행한 행렬에 대한 + 평균 평점
            svd_preds = pd.DataFrame(svd_user_predicted_ratings, columns = user_music_ratings.columns)

            # 추천 시스템 함수
            def recommend_music(svd_preds, customer_id, music_df, rating_df, num_recommendation=5):
    
                # 인덱스이므로 선택한 유저 값의 -1
                user_row_number = customer_id - 1
    
                # svd기법으로 내적 수행한 테이블에서 선택한 유저의 값을 정렬
                sorted_user_predictions = svd_preds.iloc[user_row_number].sort_values(ascending=False)
    
                # 유저의 데이터를 받아옴
                user_data = rating_df[rating_df.customer_id == customer_id]
                

                # 추천 테이블 작성
                # 유저가 들었던 음악은 제외
                recommendations = music_df[~music_df['product_title'].isin(user_data['product_title'])]

                # 정렬된 예측값 테이블과 병합
                recommendations = recommendations.merge(pd.DataFrame(sorted_user_predictions).reset_index(), on = 'product_title')

                # 중복된 노래 제거
                recommendations = recommendations.drop_duplicates(['product_title'], keep="last")
                del recommendations['customer_id']

                # 예측값을 기준으로 정렬
                recommendations = recommendations.rename(columns = {user_row_number: 'Predictions'}).sort_values('Predictions', ascending = False).iloc[:num_recommendation, :]
                return user_data, recommendations

            already_rated, predictions = recommend_music(svd_preds, int(userid), dataset, dataset, 10)
            print(predictions)
            predictions['product_title'].to_string(index=False)
            temp = []
            temp.append(predictions['product_title'].to_string(index=False))
            temp2 = []
            for i in temp:
                j = i.replace(' ','')
                temp2.append(j)
            myLists = []
            myLists = temp2[0].split("\n")
                
            return render_template('index.html', myLists=myLists)
        else:
            return render_template('login.html')
    


if __name__ == "__main__":
    application.run(host='0.0.0.0', port=int(sys.argv[1]))
