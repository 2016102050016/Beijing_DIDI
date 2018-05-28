# encoding: utf-8
# author: zhaotianhong

import os

import time

import _config
import _tools
import _get_trip_stop
import _trip_repair

PARA = _config.CONFIG

if __name__ == '__main__':
    # 24号
    time_start = time.time()
    t_start = time.time()
    START, END = PARA['date']['28'][0], PARA['date']['28'][1]
    path_dir = r'../DATA/original'
    if os.path.exists(PARA['path_out']):
        os.remove(PARA['path_out'])
    car_id = 0
    # 读取所有文件
    all_paths = _tools.get_all_csv(path_dir)
    no_data, no_stop, no_trip, wrong, read_f, ex = 0, 0, 0, 0, 0, 0
    for path in all_paths:
        read_f+=1
        try:
            # 去读数据
            data = _tools.read_data(path, START, END)
            # 切分断点
            if data:
                data_o = data[:]
                data_breakpoint = _get_trip_stop.get_breakpoint(data)
                if data_breakpoint:
                    # 得到停留点
                    data_stop = _get_trip_stop.get_stop_point(data_breakpoint, START, END)
                    # print 'stop numbers:', len(data_stop)
                    if data_stop:
                        # 计算停留点与运动点
                        trip_stop = _get_trip_stop.get_trip(data_stop, data)
                        result = _get_trip_stop.check_data(trip_stop)
                        # result = _trip_repair.repair(result)
                        if not result:
                            continue
                        car_id += 1
                        # 可视化
                        # _tools.show_map(result)
                        # 写出文件
                        # if car_id == 100:
                        #     break
                        _tools.write_to_files(result, PARA['path_out'], car_id, False)
                        # _tools.write_original_files(data_o,result,car_id)
                    else:
                        no_trip += 1
                else:
                    no_stop += 1
            else:
                no_data += 1
        except:
            ex += 1

        if read_f % 2000 == 0:
            time_run = time.time() - t_start
            print '********************************'
            print '当前进度：%s' % round((read_f / float(len(all_paths))) * 100, 2), '%'
            print '当前耗时：%s' % int((time.time() - time_start) / 60.0), 'min'
            print '识别速度：%s' % round((time_run / 2000), 4), 's/文件'
            print '总体识别率：%s' % round((car_id / float(read_f)) * 100, 2), '%'
            print '数据质量损失率：%s' % round((no_data / float(read_f)) * 100, 2), '%'
            print '停留点损失率：%s' % round((no_stop / float(read_f)) * 100, 2), '%'
            print '运动轨迹损失率：%s' % round((no_trip / float(read_f)) * 100, 2), '%'
            print '异常损失率：%s' % round((ex / float(read_f)) * 100, 2), '%'
            t_start = time.time()
