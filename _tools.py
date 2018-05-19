# encoding: utf-8
# author: zhaotianhong

import time
from math import radians, cos, sin, asin, sqrt
import os
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt


def haversine(lon1, lat1, lon2, lat2):  # 经度1，纬度1，经度2，纬度2 （十进制度数）
    '''用经纬度计算距离，单位米'''
    # 将十进制度数转化为弧度
    lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
    # haversine公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # 地球平均半径，单位为公里
    return c * r * 1000


def timestamp_to_time(timestamp):
    '''时间戳转时间'''
    time_local = time.localtime(int(timestamp))
    # 转换成新的时间格式(2016-05-05 20:28:54)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt


def time_to_timestamp(dt):
    '''时间转时间戳'''
    timeArray = time.strptime(dt, "%Y-%m-%d %H:%M:%S")
    # 转换成时间戳
    timestamp = time.mktime(timeArray)
    return int(timestamp)


def get_all_csv(f_dir):
    '''获取所有的文件'''
    path_list = []
    for file_name in os.listdir(f_dir):
        p = os.path.join(f_dir, file_name)
        path_list.append(p)
    return path_list


def read_data(path, START_TIME, END_TIME):
    '''
    读取数据：1.筛选时间段；2.筛选记录低于500条的文件；3.根据经纬度重新计算速度并标记（0：静止，1：运动）
    :param path: 文件路径
    :return: 
    '''
    # time_list用于去时间记录为重复的
    data_list, time_list = [], []
    with open(path, 'r') as f:
        for line in f:
            if len(line) > 10:
                line_arr = line[:-1].split(',')
                time_stamp = int(line_arr[2])
                if time_stamp not in time_list and time_stamp > START_TIME and time_stamp < END_TIME:
                    data_list.append([float(line_arr[0]), float(line_arr[1]), time_stamp, float(line_arr[3]),
                                      timestamp_to_time(time_stamp)])
                    time_list.append(time_stamp)
    # 记录小于500，返回空
    if len(data_list) <= 500:
        return None
    # 计算运动或者静止
    temp_data = [data_list[0]]
    temp_data[0][3] = 0
    for i in range(1, len(data_list)):
        dis = haversine(temp_data[-1][0], temp_data[-1][1], data_list[i][0], data_list[i][1])
        time_gap = abs(data_list[i][2] - temp_data[-1][2])
        v = dis / time_gap
        # 静止条件速度低于1m/s
        if v < 1:
            data_list[i][3] = 0
            temp_data.append(data_list[i])
        else:
            data_list[i][3] = 1
            temp_data.append(data_list[i])
    # 排序，按时间戳排序
    data_list = sorted(data_list, key=lambda x: x[2])
    return data_list


def show_map(merge_list):
    '''3D显示用于分析'''
    fig = plt.figure()
    ax = Axes3D(fig)
    num = 0
    for k,v in merge_list.items():
        num += 1
        x, y, z = [], [], []
        for i in v[-1]:
            x.append(i[0])
            y.append(i[1])
            z.append(i[2])
        if len(v[-1]) == 2:
            ax.plot(x, y, z, 'b')
        else:
            ax.plot(x, y, z, 'r--')

    plt.show()
