# encoding: utf-8
# author: zhaotianhong

import os
import _config
import _tools
import _get_trip_stop

PARA = _config.CONFIG

if __name__ == '__main__':
    # 24号
    START,END = PARA['date']['24'][0],PARA['date']['24'][1]
    path_dir = r'../DATA/original'
    if os.path.exists(PARA['path_out']):
        os.remove(PARA['path_out'])
    car_id = 0
    # 读取所有文件
    all_paths = _tools.get_all_csv(path_dir)
    for path in all_paths:
        print path
        # 去读数据
        data = _tools.read_data(path,START,END)
        # 切分断点
        if data:
            data_breakpoint = _get_trip_stop.get_breakpoint(data)
            if data_breakpoint:
                # 得到停留点
                data_stop = _get_trip_stop.get_stop_point(data_breakpoint,START,END)
                print 'stop numbers:',len(data_stop)
                if data_stop:
                    # 计算停留点与运动点
                    trip_stop = _get_trip_stop.get_trip(data_stop,data)
                    trip_stop = _get_trip_stop.add_virtual_point(trip_stop)
                    car_id += 1
                    # 可视化
                    # _tools.show_map(trip_stop)
                    # 写出文件
                    if car_id == 1000:
                        break
                    _tools.write_to_files(trip_stop,PARA['path_out'],car_id,False)
                else:
                    print 'no stop'
            else:
                print 'no break point'
        else:
            print 'data less'