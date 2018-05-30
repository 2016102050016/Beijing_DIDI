# encoding: utf-8
# author: zhaotianhong

import _tools

# 参数
# 间断点的划分时间
_t_breakpoint = 600

# 停留记录聚类：相邻两个记录停留的时间间隔；相邻两个点的距离
_t_cluster = 20
_d_cluster = 50

# 判断真实的停留点：通过对聚类的速度为0的集合，判断停留的真实性
# 若集合内持续时间高于3min，且集合内部速度小于1（用速度比距离好）
_t_judge_stop = 60
_v_judge_stop = 1

# 合并停留：若两个停留时间间隔短或者距离很近合并为一次停留
_t_merge_stop = 180
_d_merge_stop = 500

# 筛选运动:若运动距离很短剔除掉
_d_filter_trip = 100

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
                if len(stop_set_i) > 1:
                    potential_stop_point.append([stop_set_i[0], stop_set_i[-1]])
                    stop_set_i = []
        if len(stop_set_i) > 1:
            potential_stop_point.append([stop_set_i[0], stop_set_i[-1]])

    # step2:判断真实的停留点
    for line in potential_stop_point:
        # 停留时长
        t_gap = line[-1][2] - line[0][2]
        # 停留点集合第一个与最后一个点的距离
        dis_gap = _tools.haversine(line[-1][0], line[-1][1], line[0][0], line[0][1])
        v = dis_gap/float(t_gap)
        # 停留点识别：超过3min且在500米范围内
        if t_gap > _t_judge_stop and v < _v_judge_stop:
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
    # 添加虚拟点
    final_data = add_virtual_point(trip_set)
    return final_data


def check_data(trip_stop):
    '''
    再次筛选数据，剔除假运动轨迹与停留点
    :param trip_stop: 停留点与运动的轨迹
    :return: 
    '''
    # step1：剔除不满足的停留和运动，直接删除
    keys = sorted(trip_stop.keys())
    result, short_set, num = {}, [], 0
    for k in keys:
        v = trip_stop[k]
        # 最后筛选停留于运动：运动距离大于1km；停留时间大于3min
        if v[5] > 0 and v[5] < _d_filter_trip:
            trip_stop.pop(k)
        if v[4] < 180:
            trip_stop.pop(k)

    # step2:将剔除掉的重组：按照停留-运动-停留
    temp_list, trip_set, stop_set = [], [], []
    keys = sorted(trip_stop.keys())
    for k in keys:
        v = trip_stop[k]
        if v[5] == 0:
            if len(trip_set) > 0:
                temp_list.append(trip_set)
                trip_set = []
            stop_set.append(v)
        else:
            if len(stop_set) > 0:
                temp_list.append(stop_set)
                stop_set = []
            trip_set.append(v)
    if len(trip_set) > 0:
        temp_list.append(trip_set)
    if len(stop_set) > 0:
        temp_list.append(stop_set)

    # step3：重新计算停留时间，轨迹长度
    for t_set in temp_list:
        if len(t_set) == 1:
            result[t_set[0][-1][0][2]] = t_set[0]
        else:
            xyt, sum_t, sum_dis = [], 0, 0
            key = t_set[0][-1][0][2]
            x = t_set[0][0]
            y = t_set[0][1]
            sum_t = t_set[-1][-1][-1][2] - t_set[0][-1][0][2]
            for v in t_set:
                xyt.extend(v[-1])
                sum_dis += v[5]
            result[key] = [x, y, x, y, sum_t, sum_dis, xyt]
    keys = sorted(result.keys())

    # step4：可视化部分：修复不相连的轨迹
    last_xyt = None
    for k in keys:
        if last_xyt and last_xyt not in result[k][-1]:
            result[k][-1].insert(0, last_xyt)
        if result[k][5] == 0:
            result[k][-1][-1][0] = result[k][-1][0][0]
            result[k][-1][-1][1] = result[k][-1][0][1]
            result[k][-1] = [result[k][-1][0], result[k][-1][-1]]
        last_xyt = result[k][-1][-1]
    return result


def add_virtual_point(trip_stop):
    '''
    添加虚拟点：为了保证合理性，两边都补充虚拟点
    :param trip_stop: 
    :return: 
    '''
    # 若只有一个停留点直接返回
    if len(trip_stop) == 1:
        return trip_stop
    # 停留和之后一个运动之间距离差距大于500米，添加虚拟点（位置为该停留点，时间28km/h补充）
    keys = sorted(trip_stop.keys())
    for i in range(1, len(keys) - 1, 2):
        trip = trip_stop[keys[i]]
        # 前一个停留
        stop_head = trip_stop[keys[i - 1]]
        # 后一个停留
        stop_back = trip_stop[keys[i + 1]]
        dis_gap_head = _tools.haversine(stop_head[-1][-1][0], stop_head[-1][-1][1], trip[-1][0][0], trip[-1][0][1])
        dis_gap_back = _tools.haversine(stop_back[-1][-1][0], stop_back[-1][-1][1], trip[-1][-1][0], trip[-1][-1][1])
        # 若间断相差500m以上，用28km/h（7.8m/s）进行补充
        if dis_gap_head > _d_add_virtual_point:
            t = stop_head[-1][-1][2] - int(dis_gap_head / 7.8)
            add_record = [stop_head[0], stop_head[1], t, _tools.timestamp_to_time(t)]
            trip[-1].insert(0, add_record)
            trip[4] = trip[4] + int(dis_gap_head / 7.8)  # trip的时间增加
            trip[5] = trip[5] + int(dis_gap_head)  # trip的距离增长
            # 前面停留点参数的变化
            stop_head[4] = t - stop_head[-1][0][2]
            stop_head[-1][-1][2] = t

        if dis_gap_back > _d_add_virtual_point:
            t = stop_back[-1][0][2] + int(dis_gap_head / 7.8)
            add_record = [stop_back[0], stop_back[1], t, _tools.timestamp_to_time(t)]
            trip[-1].append(add_record)
            trip[4] = trip[4] + int(dis_gap_head / 7.8)  # trip的时间增加
            trip[5] = trip[5] + int(dis_gap_head)  # trip的距离增长
            # 前面停留点参数的变化
            stop_back[4] = stop_back[-1][-1][2] - t
            stop_back[-1][0][2] = t

    return trip_stop
