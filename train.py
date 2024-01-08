import json
import glob
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GridSearchCV
# 获取所有json文件
json_files = glob.glob('train/json_file/*.json')

data = []
labels = []
track_num = 15
# 遍历所有文件
for file in json_files:
    with open(file, 'r') as f:
        # 加载json文件
        file_data = json.load(f)
        # 过滤掉数据量小于20帧的文件
        for i in range(len(file_data) - track_num + 1):
            pose_track = []
            file_data[i:i+track_num]
            for item in file_data[i:i+track_num]:
                pose_track.extend(item["track"])
            pose_track = np.array(pose_track)
            data.append(pose_track)
            labels.append(file_data[i+track_num-1]['result'])

# 将数据和标签转换为numpy数组
data = np.array(data)
labels = np.array(labels)
X_train, X_test, y_train, y_test = train_test_split(data, labels, test_size=0.1, random_state=42)
random_state = 42
# 定义要调优的参数

# 创建一个基础模型
rf = RandomForestClassifier(random_state=random_state, n_jobs=-1, oob_score=True, n_estimators=70, max_features='sqrt', criterion='entropy')

# # 实例化GridSearchCV
# grid_search = GridSearchCV(estimator = rf, param_grid = param_grid, 
#                           cv = 3, n_jobs = -1, verbose = 2)

# # 拟合GridSearchCV
# grid_search.fit(X_train.reshape(len(X_train), -1), y_train)

# 打印最佳参数
# print(grid_search.best_params_)

# # 使用最佳参数预测测试集
# best_grid = grid_search.best_estimator_
# y_pred = best_grid.predict(X_test.reshape(len(X_test), -1))

# rf.fit(X_train.reshape(len(X_train), -1), y_train)
rf.fit(data.reshape(len(data), -1), labels)
y_pred = rf.predict(X_test.reshape(len(X_test), -1))
# 计算并打印准确率
accuracy = accuracy_score(y_test, y_pred)
print('Accuracy:', accuracy)
# 保存模型
import joblib
joblib.dump(rf, 'train/model/model.pkl')

