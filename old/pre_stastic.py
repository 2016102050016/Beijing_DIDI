# encoding: utf-8
# file: initial_solution.py
# author: zhaotianhong
# time: 2018/4/17 15:51

import time
from math import radians, cos, sin, asin, sqrt
import os


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
    data_list = sorted(temp_data, key=lambda x: x[2])
    return data_list


def get_each_sec(data_list):
    '''
    根据断点切割轨迹：1.间断时间高于半个小时（1800s）切分；
    :param data_list: 读取到的高于500记录的数据，且标记运动停留
    :return: 切分好的字典
    '''
    data_sec, sec, sec_num = {}, [], 0
    t = data_list[0][2]
    sec = [data_list[0]]
    for i in range(1, len(data_list) - 1):
        time_span = data_list[i][2]
        # 两个记录只差相差1800s，切分
        if time_span - t > 1800:
            data_sec[sec_num] = sec
            sec = [data_list[i]]
            sec_num += 1
        else:
            sec.append(data_list[i])
        t = time_span
    if len(sec) > 0:
        data_sec[sec_num] = sec

    # r = merge_sec(data_sec)
    return data_sec


def merge_sec(data_sec):
    '''
    把两端切开的轨迹进行融合（由于隧道等因素造成的间断），暂时没用（北京没有较长隧道）
    :param data_sec: 
    :return: 
    '''
    merge_data, temp_data = [], []
    for k, v in data_sec.items():
        if k == 0:
            end = v[-1]
            temp_data.append(0)
            continue
        else:
            start = v[0]
            dis = haversine(end[0], end[1], start[0], start[1])
            # 距离相差20km，且时间小于**
            if dis > 20000:
                temp_data.append(1)
            else:
                temp_data.append(0)
    for i in range(len(temp_data)):
        if temp_data[i] == 0:
            merge_data.append(data_sec[i])
        else:
            merge_data[-1].extend(data_sec[i])
    data_sec = {}
    for i in range(len(merge_data)):
        data_sec[i] = merge_data[i]
    return data_sec


def get_stop_point(data_sec):
    '''
    根据标记的运动状态筛选所有静止点
    :param data_sec: 
    :return: 
    '''
    data_stop = {}
    for k, v in data_sec.items():
        sec_i = []
        for i in range(len(v)):
            if float(v[i][3]) == 0:
                sec_i.append(v[i])
        # 一段轨迹有静止点保留
        if len(sec_i) > 0:
            data_stop[k] = sec_i
    # 一个文件都无静止，返回空
    if len(data_stop) > 0:
        return data_stop
    else:
        return None


def get_real_stop(data_stop, START_TIME, END_TIME):
    '''
    找出真实的静止点：1.找出轨迹之间的停留；2.轨迹内部停留点聚类；3.轨迹内部停留段筛选；4.对凌晨停留点进行补充；5.停留点融合（合并）
    :param data_stop: 标记速度为零的全部点
    :param START_TIME: 这一天的开始时间戳
    :param END_TIME: 结束时间戳
    :return: 
    '''
    real_stop_point, trun = [], -1
    for k, v in data_stop.items():
        stop_set_i, all_stop_set = [], []
        # 两个间断之间的停留
        trun += 1
        if trun == 0:
            first_f = v[-1]
        else:
            # step1：找出两个轨迹之间的静止点：1.若两个轨迹之间首尾相差3km以上，用28km/h进行轨迹补充
            time_sup = 0
            end_f = v[0]
            dis = haversine(first_f[0], first_f[1], end_f[0], end_f[1])
            end_time = end_f[2]
            if dis > 3000:
                # 按照28km/h补充
                time_sup = int(dis / 8)
                t_gap = end_f[2] - time_sup
                # 减少的时间不能小于上一段的结尾
                end_time = t_gap if t_gap >= first_f[2] else first_f[2] + 180
            the_point = [first_f[2], first_f[0], first_f[1], first_f[0], first_f[1], timestamp_to_time(first_f[2]),
                         timestamp_to_time(end_time), end_f[2] - first_f[2], 0]
            real_stop_point.append(the_point)
            # 补充的运动起始点
            v.insert(0, [first_f[0], first_f[1], end_f[2] - time_sup, 0, timestamp_to_time(end_f[2] - time_sup)])
            # 收尾：下一个间断轨迹的起始点
            first_f = v[-1]

        # step2:一段轨迹的停留点聚类：两个停留相差120s视为一个停留集合
        for i in range(len(v) - 1):
            time_gap = v[i + 1][2] - v[i][2]
            # 两个停留点之间间隔小于120s：认为是一次停留
            if time_gap < 120:
                stop_set_i.append(v[i])
            else:
                if len(stop_set_i) > 0:
                    all_stop_set.append(stop_set_i)
                    stop_set_i = []
        if len(stop_set_i) > 0:
            all_stop_set.append(stop_set_i)

        # step3：补充凌晨的停留点
        if k == 0:
            # 第一个停留点必须大于10min
            if v[0][2] - START_TIME < 180:
                the_point = [START_TIME, v[0][0], v[0][1], v[0][0], v[0][1], timestamp_to_time(START_TIME),
                             timestamp_to_time(v[0][2] + 180), v[0][2] - START_TIME, 0]
                real_stop_point.append(the_point)
                START_TIME = v[-1][2]
            else:
                the_point = [START_TIME, v[0][0], v[0][1], v[0][0], v[0][1], timestamp_to_time(START_TIME),
                             timestamp_to_time(v[0][2]), v[0][2] - START_TIME, 0]
                real_stop_point.append(the_point)
                START_TIME = v[-1][2]

        # step4：对聚类的停留点集合进行筛选：停留时间大于3分钟，范围小于200m（避免定位精度影响）为真正的停留点
        for v in all_stop_set:
            first = v[0]
            last = v[-1]
            time_gap = last[2] - first[2]
            dis_gap = haversine(last[0], last[1], first[0], first[1])
            # 停留点集合时间大于3min，范围小于200m
            if time_gap > 180 and dis_gap < 200:
                the_point = [first[2], first[0], first[1], first[0], first[1], timestamp_to_time(first[2]),
                             timestamp_to_time(last[2]), last[2] - first[2], 0]
                real_stop_point.append(the_point)

    # step5：最后一次停留到这一天的结束为一次停留(条件是停留时间大于3min)
    if len(all_stop_set) > 0:
        index = len(all_stop_set) - 1
        if END_TIME - all_stop_set[index][-1][2] > 180:
            the_point = [all_stop_set[index][-1][2], all_stop_set[index][-1][0], all_stop_set[index][-1][1],
                         all_stop_set[index][-1][0], all_stop_set[index][-1][1],
                         timestamp_to_time(all_stop_set[index][-1][2]), timestamp_to_time(END_TIME),
                         END_TIME - all_stop_set[index][-1][2], 0]
            real_stop_point.append(the_point)

    return merge_real_stop(real_stop_point)


def merge_real_stop(real_stop_point):
    '''
    对真正的停留点进行融合（合并）：1.合并条件两个停留点之间时间间隔小于5min，或者距离小于1km
    :param real_stop_point: 真实停留点
    :return: 
    '''
    merge_list, temp_list = [], []
    temp_list.append([real_stop_point[0]])
    for i in range(1, len(real_stop_point)):
        one = temp_list[-1][-1]
        two = real_stop_point[i]
        # 两个停留点之间距离差与时间差
        dis = haversine(one[1], one[2], two[1], two[2])
        t_gap = time_to_timestamp(two[5]) - time_to_timestamp(one[6])
        if t_gap < 300 or dis < 1000:
            temp_list[-1].append(real_stop_point[i])
        else:
            temp_list.append([real_stop_point[i]])
    for line in temp_list:
        merge_list.append(
            [time_to_timestamp(line[-1][5]), line[0][1], line[0][2], line[0][1], line[0][2], line[0][5], line[-1][6],
             time_to_timestamp(line[-1][6]) - time_to_timestamp(line[0][5]), 0])
    return merge_list


def get_trip(data_sec, real_stop_point):
    '''
    找出运动轨迹：
    :param data_sec: 原始数据
    :param real_stop_point: 真实的停留点
    :return: 
    '''
    trip,trip_xy, total_dis = [], {},0
    dis, index,temp_xy = 0, 0,[]
    # 全部原始数据，已做分割
    for k, v in data_sec.items():
        one_num = len(v)
        for i in range(one_num):
            t = int(v[i][2])
            if i == one_num - 1:
                d = 0
            else:
                d = haversine(v[i][0], v[i][1], v[i + 1][0], v[i + 1][1])
                if d > 2000:
                    return None
                temp_xy.append((v[i][0], v[i][1],time_to_timestamp(v[i][-1])))
            dis += d
            try:
                if t == time_to_timestamp(real_stop_point[index + 1][5]):
                    trip.append(
                        [time_to_timestamp(real_stop_point[index][6]), real_stop_point[index][1],
                         real_stop_point[index][2],
                         real_stop_point[index + 1][1], real_stop_point[index + 1][2], real_stop_point[index][6],
                         real_stop_point[index + 1][5],
                         time_to_timestamp(real_stop_point[index + 1][5]) - time_to_timestamp(
                             real_stop_point[index][6]), int(dis)])
                    trip_xy[trip[-1][0]] = temp_xy
                    temp_xy = []
                    index += 1
                    total_dis += dis
                    dis = 0
                if index == len(real_stop_point) - 1:
                    return trip,trip_xy
            except:
                return None
    # 总运动距离大于1000km或者小于3km，筛选掉
    if total_dis > 1000000 or total_dis <= 3000:
        return None
    return trip,trip_xy


def merge_stop_trip(stop, trip):
    '''
    停留和运动融合：1.筛选假的运动点；2.对静止点进行融合
    :param stop: 静止点
    :param trip: 运动点
    :return: 
    '''
    for i in stop:
        trip.append(i)
    merge_list = sorted(trip, key=lambda x: x[0])

    # 筛选假的运动点
    for line in merge_list:
        if line[-1] != 0:
            v = line[-1] / line[-2]
            if v < 3 and line[-1] < 1000:
                merge_list.pop(merge_list.index(line))
                continue

    # 对零点进行融合
    r_list, wrong = [], []
    for line in merge_list:
        if line[-1] == 0:
            wrong.append(line)
        else:
            if len(wrong) > 1:
                the_line = [wrong[0][0], wrong[0][1], wrong[0][2], wrong[-1][3], wrong[-1][4], wrong[0][5],
                            wrong[-1][6], time_to_timestamp(wrong[-1][6]) - time_to_timestamp(wrong[0][5]), 0]
                r_list.append(the_line)
                wrong = []
            else:
                r_list.append(wrong[0])
                wrong = []
            r_list.append(line)
    if len(wrong) > 1:
        the_line = [wrong[0][0], wrong[0][1], wrong[0][2], wrong[-1][3], wrong[-1][4], wrong[0][5],
                    wrong[-1][6], time_to_timestamp(wrong[-1][6]) - time_to_timestamp(wrong[0][5]), 0]
        r_list.append(the_line)
    else:
        r_list.append(merge_list[-1])
    return r_list


def show_map(merge_list):
    '''3D显示用于分析'''
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = Axes3D(fig)

    num = 0
    for line in merge_list:
        num += 1
        x, y, z = [], [], []
        for i in line[-1]:
            x.append(i[0])
            y.append(i[1])
            z.append(i[2])
        if num % 2 == 0:
            ax.plot(x, y, z, 'r--')
        else:
            ax.plot(x, y, z, 'b')
    plt.show()

def get_show_xy(result,trip_xy):
    for line in result:
        if line[0] in trip_xy.keys():
            line.append(trip_xy[line[0]])
        else:
            line.append([(line[3],line[4],time_to_timestamp(line[5])),(line[3],line[4],time_to_timestamp(line[6]))])

    # 检验
    for i in range(len(result)-1):
        f = result[i][-1]
        s = result[i+1][-1]
        if f[-1][:-1] == s[0][:-1]:
            continue
        else:
            return None

    return result

def write_xy(result,path,car_id):

    with open(path,'a+') as f:
        for line in result:
            TYPE = 'TRIP'
            if line[8] == 0:
                TYPE = 'STAY'
            xyt_str = ''
            s_t = time_to_timestamp(line[5])
            e_t = time_to_timestamp(line[6])
            for xyt in line[9]:
                if xyt[2] < s_t or xyt[2] > e_t:
                    continue
                else:
                    xyt_str += str(xyt[0])+','+ str(xyt[1])+','+ str(xyt[2])+' '

            # xyt_e = xyt_str + str(line[3])+','+ str(line[4])+','+ str(e_t)
            # xyt_str = str(line[1])+','+ str(line[2])+','+ str(s_t)+' '+xyt_e

            f.write(str(car_id)+'\t'+TYPE+'\t'+str(line[5])+'\t'+str(line[6])+'\t'+str(line[8])+'\t'+str(line[7])+'\t'+xyt_str+'\n')

def write_o(path,data):
    with open(path,'w') as fw:
        for line in data:
            fw.write(str(line[0])+','+str(line[1])+','+str(line[2])+','+str(line[3])+','+str(line[4])+','+'\n')




def stastic(all_files,car_id_list, path_out):
    START_TIME, END_TIME = 1448380800, 1448467200  # 25 号1448467200
    path_show = r'E:\sc\beijingdidi\beijingDIDI_SHOW\show.txt'
    path_dir_o = r'E:\sc\beijingdidi\beijingDIDI_SHOW\Original'

    car_id_xy = 0

    t_start = time.time()
    tt1 = time.time()
    fw = open(path_out, 'w')
    car_id_num, no_data, no_stop, no_trip, wrong, read_f, ex = 0, 0, 0, 0, 0, 0, 0
    for path in all_files:
        car_id = car_id_list[read_f]
        read_f += 1
        # print(path)
        # try:
        data_list = read_data(path, START_TIME, END_TIME)
        try:
            if data_list:
                data_sec = get_each_sec(data_list)
                data_stop = get_stop_point(data_sec)
                # 判断有无停留点
                if data_stop:
                    real_stop_point = get_real_stop(data_stop, START_TIME, END_TIME)
                    trip,trip_xy = get_trip(data_sec, real_stop_point)
                    # 判断有无trip
                    if trip:
                        result = merge_stop_trip(real_stop_point, trip)
                        r = get_show_xy(result,trip_xy)
                        if r:
                            car_id_xy += 1
                            if car_id_xy < 1000:
                                path_o = path_dir_o+'\\'+str(car_id_xy)+'.txt'
                                show_map(r)
                                print path_o
                                write_xy(r,path_show,car_id_xy)
                                write_o(path_o,data_list)
                            else:
                                break
                        # show_map(result)
                        car_id_num+=1
                        # for n in result:
                        #     fw.write(str(car_id) + '\t' + str(n[0]) + '\t' + str(n[1]) + '\t' + str(n[2]) + '\t' + str(
                        #         n[3]) + '\t' + str(n[4]) + '\t' + str(n[5]) + '\t' + str(n[6]) + '\t' + str(
                        #         n[7]) + '\t' + str(n[8]) + '\n')
                    else:
                        no_trip += 1
                else:
                    no_stop += 1
            else:
                no_data += 1
        except:
            ex += 1
        if read_f % 2000 == 0:
            time_run = time.time() - tt1
            print('********************************')
            print('当前进度：%s' % round((read_f / len(all_files)) * 100, 2), '%')
            print('当前耗时：%s'%int((time.time()-t_start)/60),'min')
            print('识别速度：%s' % round((time_run / 2000), 4), 's/文件')
            print('总体识别率：%s' % round((car_id_num / read_f) * 100, 2), '%')
            print('数据质量损失率：%s' % round((no_data / read_f) * 100, 2), '%')
            print('停留点损失率：%s' % round((no_stop / read_f) * 100, 2), '%')
            print('运动轨迹损失率：%s' % round((no_trip / read_f) * 100, 2), '%')
            print('异常损失率：%s' % round((ex / read_f) * 100, 2), '%')
            tt1 = time.time()
    fw.close()


def file_name(file_dir):
    '''读取所有文件，包括子文件夹'''
    print('file location:', file_dir)
    L ,NAME = [],[]
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            L.append(os.path.join(root, file))
            NAME.append(file[:-4])
    print('file number:', len(L))
    return L,NAME


if __name__ == '__main__':
    p_f = r'E:\sc\beijingdidi\newdata'

    path_out = r'E:\sc\beijingdidi\stastic-tt.txt'
    t1 = time.time()
    print('*** starting time:', timestamp_to_time(t1))
    list,car_id = file_name(p_f)
    stastic(list, car_id,path_out)
    print('*** ending time:', timestamp_to_time(time.time()))
    print('spending time:', time.time() - t1)
