# encoding: utf-8
# author: zhaotianhong

import _tools

def get_breakpoint(data_list):
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
        if time_span - t > 1200:
            data_sec[sec_num] = sec
            sec = [data_list[i]]
            sec_num += 1
        else:
            sec.append(data_list[i])
        t = time_span
    if len(sec) > 0:
        data_sec[sec_num] = sec
    return data_sec


def pre_stop_point(data_breakpoint, START_TIME, END_TIME):
    '''
    预处理停留点，挑选出间断点视为真正停留
    :param data_breakpoint: 
    :param START_TIME: 
    :param END_TIME: 
    :return: 
    '''
    # 所有速度为零的记录；间断点视为真实的停留点
    data_stop, real_stop_point = {}, []
    start_s = [START_TIME]
    for k, v in data_breakpoint.items():
        sec_i, stop_line = [], []
        real_stop_point.append([[v[0][0], v[0][1], start_s[-1]], [v[0][0], v[0][1], v[0][2]]])
        start_s.append(v[-1][2])
        for i in range(len(v)):
            if float(v[i][3]) == 0:
                sec_i.append(v[i])
        # 一段轨迹有静止点保留
        if len(sec_i) > 0:
            data_stop[k + 1] = sec_i
    # 最后一个点与下一天凌晨的停留点
    last_point = data_breakpoint[len(data_breakpoint) - 1][-1]
    real_stop_point.append([[last_point[0], last_point[1], last_point[2]], [last_point[0], last_point[1], END_TIME]])

    # 一个文件都无静止，返回空
    if len(data_stop) > 0:
        return data_stop, real_stop_point
    else:
        return None


def get_stop_point(data_breakpoint, START_TIME, END_TIME):
    '''
    找出真实的静止点：1.找出轨迹之间的停留；2.轨迹内部停留点聚类；3.轨迹内部停留段筛选；4.对凌晨停留点进行补充；5.停留点融合（合并）
    :param data_stop: 标记速度为零的全部点
    :param START_TIME: 这一天的开始时间戳
    :param END_TIME: 结束时间戳
    :return: 
    '''
    potential_stop_point, stop_merge = [], []
    # 停留点预处理，得到间断点直接视为真实停留
    data_stop, real_stop_point = pre_stop_point(data_breakpoint, START_TIME, END_TIME)
    # 若没有停留直接返回
    if not data_stop:
        return None

    # step1:停留点聚类：在每一段轨迹中寻找潜在停留点
    for k, v in data_stop.items():
        stop_set_i = []
        # 两个停留相差120s或者距离在500米内视为一个停留点集合
        for i in range(len(v) - 1):
            time_gap = v[i + 1][2] - v[i][2]
            dis_gap = _tools.haversine(v[i][0], v[i][1], v[i + 1][0], v[i + 1][1])
            # 两个停留点之间间隔小于120s或者距离500m内
            if time_gap < 120 or dis_gap < 500:
                stop_set_i.append(v[i])
            else:
                if len(stop_set_i) > 0:
                    potential_stop_point.append([stop_set_i[0], stop_set_i[-1]])
                    stop_set_i = []
        if len(stop_set_i) > 0:
            potential_stop_point.append([stop_set_i[0], stop_set_i[-1]])

    # step2:判断真实的停留点
    for line in potential_stop_point:
        # 停留时长
        t_gap = line[-1][2] - line[0][2]
        # 停留点集合第一个与最后一个点的距离
        dis_gap = _tools.haversine(line[-1][0], line[-1][1], line[0][0], line[0][1])
        # 停留点识别：超过3min且在500米范围内
        if t_gap > 180 and dis_gap < 1500:
            real_stop_point.append(line)

    # step3：对停留进行融合
    real_stop_point = sorted(real_stop_point, key=lambda x: x[0][2])
    stop_merge = [real_stop_point[0]]
    for i in range(len(real_stop_point) - 1):
        t_gap = real_stop_point[i + 1][0][2] - stop_merge[-1][-1][2]
        dis_gap = _tools.haversine(real_stop_point[i + 1][0][0], real_stop_point[i + 1][0][1],
                                   stop_merge[-1][-1][0], stop_merge[-1][-1][1])

        if dis_gap < 500 or t_gap < 180:
            # 若满足融合条件：两个停留点集合融合
            stop_merge[-1].append(real_stop_point[i + 1][-1])
        else:
            stop_merge.append(real_stop_point[i + 1])

    # step4:标准化输出
    standard_stop = {}
    for s in stop_merge:
        # 停留时长
        t_gap = s[-1][2] - s[0][2]
        # 第一个点与最后一个点统一坐标
        s[-1][0] = s[0][0]
        s[-1][1] = s[0][1]
        # 用于可视化画线段与调试识别时间
        stop_line = [[s[0][0], s[0][1], s[0][2], _tools.timestamp_to_time(s[0][2])],
                     [s[0][0], s[0][1], s[-1][2], _tools.timestamp_to_time(s[-1][2])]]
        standard_stop[s[0][2]] = [s[0][0], s[0][1], s[0][0], s[0][1], t_gap, 0, stop_line]

    return standard_stop


def get_trip(stop_point, data_original):
    trip_set, dis, xyt = {}, 0, []
    # 遍历原始文件
    stop_num = 0
    stop_point_keys = sorted(stop_point.keys())
    for line in data_original:
        if stop_num == len(stop_point_keys) - 1:
            break
        trip_start = stop_point[stop_point_keys[stop_num]][-1][-1][2]
        trip_end = stop_point[stop_point_keys[stop_num + 1]][-1][0][2]
        if line[2] == trip_start:
            xyt = [[line[0], line[1], line[2], line[4]]]
        if line[2] > trip_start:
            dis += _tools.haversine(line[0], line[1], xyt[-1][0], xyt[-1][1])
            xyt.append([line[0], line[1], line[2], line[4]])
        # 一段运动总是在两个停留之间：所以遇到停留点输出一段运动
        if line[2] == trip_end:
            dis += _tools.haversine(line[0], line[1], xyt[-1][0], xyt[-1][1])
            xyt.append([line[0], line[1], line[2], line[4]])
            trip_set[xyt[0][2]] = [xyt[0][0], xyt[0][1], xyt[-1][0], xyt[-1][1], xyt[-1][2] - xyt[0][2], int(dis), xyt]
            dis = 0
            stop_num += 1

    # 运动与停留合并
    for k, v in stop_point.items():
        trip_set[k] = v

    keys = sorted(trip_set.keys())
    # 剔除假运动轨迹：gps记录小于50，或者运动距离小于1km
    final_data = check_data(trip_set, keys)
    return final_data


def check_data(trip_stop, keys):
    '''
    再次筛选数据，剔除假运动轨迹
    :param trip_stop: 
    :param keys: 
    :return: 
    '''
    result, short_set, num = {}, [], 0
    for k in keys:
        v = trip_stop[k]
        # 若gps记录点小于50条且运动距离小于1km视为假运动
        if len(v[-1]) < 50 or v[5] < 1000:
            short_set.append(v)
        else:
            # 只有静止点
            if len(short_set) == 1:
                key = short_set[0][-1][0][2]
                result[key] = short_set[0]
                result[k] = v
            # 有静止点与假运动点,归于一个静止点
            if len(short_set) > 1:
                start_ = short_set[0][-1][0]
                end_ = short_set[-1][-1][-1]
                result[start_[2]] = [short_set[0][0], short_set[0][1], short_set[0][0], short_set[0][1],
                                     end_[2] - start_[2], 0, [start_, [start_[0], start_[1], end_[2], end_[3]]]]
                result[k] = v
            # 直接为真运动
            if len(short_set) == 0:
                result[k] = v
            short_set = []
    # 若只有停留点
    if len(result) > 0:
        # 填充最后一个停留点
        max_key = max(result.keys())
        time_end = result[max_key][-1][-1][2]
        # 停留的开始时间
        trip_stop[keys[-1]][-1][0][2] = time_end
        result[time_end] = trip_stop[keys[-1]]

        return result
    else:
        return trip_stop
