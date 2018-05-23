# encoding: utf-8
# author: zhaotianhong

import _tools

# 参数
# 间断点的划分时间
_t_breakpoint = 1200

# 停留记录聚类：相邻两个记录停留的时间间隔；相邻两个点的距离
_t_cluster = 120
_d_cluster = 500

# 判断真实的停留点：通过对聚类的速度为0的集合，判断停留的真实性
# 若集合内持续时间高于3min，或者行驶小于**（m）则为真实停留
_t_judge_stop=180
_d_judge_stop=500

# 合并停留：对于判断出的真实停留，若两个时间或者距离相隔很近合并为一次停留
_t_merge_stop = 180
_d_merge_stop = 500

# 筛选运动:若运动距离很短剔除掉
_d_filter_trip = 1000

# 添加虚拟点：若停留点与下一个运动之间间断500米以上距离，添加虚拟点在停留点出
_d_add_virtual_point = 500


def get_breakpoint(data_list):
    '''
    根据断点切割轨迹：1.间断时间高于半个小时（20min）切分；
    :param data_list: 读取到的高于500记录的数据，且标记运动停留
    :return: 切分好的字典
    '''
    data_sec, sec = [], []
    t = data_list[0][2]
    sec = [data_list[0]]
    for i in range(1, len(data_list) - 1):
        time_span = data_list[i][2]
        # 两个记录只差相差1800s，切分
        if time_span - t > _t_breakpoint:
            if len(sec) > 0:
                data_sec.append(sec)
                sec = []
        else:
            sec.append(data_list[i])
        t = time_span
    if len(sec) > 0:
        data_sec.append(sec)

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
    data_stop, real_stop_point, num = {}, [], 0
    start_s = [START_TIME]
    for v in data_breakpoint:
        sec_i, stop_line = [], []
        real_stop_point.append([[v[0][0], v[0][1], start_s[-1]], [v[0][0], v[0][1], v[0][2]]])
        start_s.append(v[-1][2])
        for i in range(len(v)):
            if float(v[i][3]) == 0:
                sec_i.append(v[i])
        # 一段轨迹有静止点保留
        if len(sec_i) > 0:
            data_stop[num + 1] = sec_i
            num += 1
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
    这个部分的参数非常重要！
    找出真实的停留点：1.轨迹内部停留点聚类；2.判断停留；3.停留点融合（合并）
    :param data_breakpoint: 标记速度为零的全部点
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
            if time_gap < _t_cluster and dis_gap < _d_cluster:
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
        if t_gap > _t_judge_stop and dis_gap < _d_judge_stop:
            real_stop_point.append(line)

    # step3：对停留进行融合
    real_stop_point = sorted(real_stop_point, key=lambda x: x[0][2])
    stop_merge = [real_stop_point[0]]
    for i in range(len(real_stop_point) - 1):
        t_gap = real_stop_point[i + 1][0][2] - stop_merge[-1][-1][2]
        dis_gap = _tools.haversine(real_stop_point[i + 1][0][0], real_stop_point[i + 1][0][1],
                                   stop_merge[-1][-1][0], stop_merge[-1][-1][1])

        if dis_gap < _d_merge_stop or t_gap < _t_merge_stop:
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
    data_original = sorted(data_original, key=lambda x: x[2])

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
    :param trip_stop: 停留点与运动的轨迹
    :param keys: 
    :return: 
    '''
    result, short_set, num = {}, [], 0
    for k in keys:
        v = trip_stop[k]
        # 若gps记录点小于50条且运动距离小于1km视为假运动
        if v[5] > 0 and v[5] < _d_filter_trip:
            short_set.append(v)
            trip_stop.pop(k)

    short_set = []
    keys = sorted(trip_stop.keys())
    for k in keys:
        v = trip_stop[k]
        if v[5] == 0:
            short_set.append(v)
        else:
            the_k = short_set[0][-1][0][2]
            # 位置统一
            short_set[-1][-1][-1][0] = short_set[0][-1][0][0]
            short_set[-1][-1][-1][1] = short_set[0][-1][0][1]
            the_v = [short_set[0][0], short_set[0][1], short_set[0][0], short_set[0][1],
                     short_set[-1][-1][-1][2] - short_set[0][-1][0][2], 0,
                     [short_set[0][-1][0], short_set[-1][-1][-1]]]
            result[the_k] = the_v
            # 真实trip写入
            result[k] = v
            short_set = []

    if len(short_set) > 0:
        the_k = short_set[0][-1][0][2]
        # 位置统一
        short_set[-1][-1][-1][0] = short_set[0][-1][0][0]
        short_set[-1][-1][-1][1] = short_set[0][-1][0][1]
        the_v = [short_set[0][0], short_set[0][1], short_set[0][0], short_set[0][1],
                 short_set[-1][-1][-1][2] - short_set[0][-1][0][2], 0,
                 [short_set[0][-1][0], short_set[-1][-1][-1]]]
        result[the_k] = the_v
        short_set = []

    return result


def add_virtual_point(trip_stop):
    # 若只有一个停留点直接返回
    if len(trip_stop) == 1:
        return trip_stop
    # 停留和之后一个运动之间距离差距大于500米，添加虚拟点（位置为该停留点，时间28km/h补充）
    keys = sorted(trip_stop.keys())
    for i in range(0, len(keys) - 1, 2):
        stop = trip_stop[keys[i]]
        trip = trip_stop[keys[i + 1]]
        dis_gap = _tools.haversine(stop[-1][-1][0], stop[-1][-1][1], trip[-1][0][0], trip[-1][0][1])
        # 若间断相差500m以上，用28km/h（7.8m/s）进行补充
        if dis_gap > _d_add_virtual_point:
            t = stop[-1][-1][2] - int(dis_gap / 7.8)
            if t - stop[-1][0][2] > 180:
                add_record = [stop[0], stop[1], t, 0, _tools.timestamp_to_time(t)]
                trip[-1].insert(0, add_record)
            else:
                return None

    # 凌晨的停留太短，直接舍弃
    first_key = keys[0]
    end_key = keys[0]
    if trip_stop[first_key][4] < 180:
        trip_stop.pop(first_key)
    if trip_stop[end_key][4] < 180:
        trip_stop.pop(end_key)

    return trip_stop
