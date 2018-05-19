# Beijing_DIDI
## 描述
对某一天滴滴gps轨迹识别其`停留点`与`运动轨迹`,统计其停留点的个数，停留长，运动轨迹长度，运动时间。
## 文件
* `main.py`：入口
* `_get_trip_stop`：对整条轨迹识别出停留点与运动轨迹
* `_write_to_shp`：将轨迹输出为shape文件
## 依赖
`ogr`,`matplotlib`
## 流程
* 1. 间断点识别
* 2. 停留点聚类
* 3. 识别与融合停留点
* 4. 轨迹识别

![](https://github.com/zhaotianhong/Beijing_DIDI/blob/master/Figure_1.png)
