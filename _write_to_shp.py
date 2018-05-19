# encoding: utf-8
# file: _write_to_shp.py
# author: zhaotianhong
# time: 2018/5/17 9:33

import os, sys
from osgeo import gdal
from osgeo import ogr
from osgeo import osr


def read_data(path):
    '''
    读取有xyt的识别停留点与运动的数据
    :param path: 读取文件保存路径
    :return: 
    '''
    data = []
    with open(path, 'r') as f:
        for line in f:
            line_arr = line[:-1].split('\t')
            plyline = line_arr[-1]
            data.append(
                [int(line_arr[0]), line_arr[1], line_arr[2], line_arr[3], int(line_arr[4]), int(line_arr[5]), plyline])
    return data



def createShap(data):
    '''
    创建shap文件
    :param data: 
    :return: 
    '''
    # 输出文件夹
    path_out = r'E:\python\beijingdidi_show\result'

    # 为了支持中文路径，请添加下面这句代码
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
    # 为了使属性表字段支持中文，请添加下面这句
    gdal.SetConfigOption("SHAPE_ENCODING", "")
    # 注册所有的驱动
    ogr.RegisterAll()
    # 数据格式的驱动
    driver = ogr.GetDriverByName('ESRI Shapefile')
    ds = driver.CreateDataSource(path_out)
    shapLayer = ds.CreateLayer("didi_trip_stay", geom_type=ogr.wkbLineString25D)
    # 添加字段
    # 先创建一个叫car_ID的字段
    oFieldID = ogr.FieldDefn("car_ID", ogr.OFTInteger)
    shapLayer.CreateField(oFieldID, 1)
    # type字段
    oFieldtype = ogr.FieldDefn("type", ogr.OFTString)
    shapLayer.CreateField(oFieldtype, 1)
    # 开始时间字段
    oFieldstart = ogr.FieldDefn("start", ogr.OFTString)
    shapLayer.CreateField(oFieldstart, 1)

    oFieldend = ogr.FieldDefn("end", ogr.OFTString)
    shapLayer.CreateField(oFieldend, 1)

    oFielddis = ogr.FieldDefn("distance", ogr.OFTInteger)
    shapLayer.CreateField(oFielddis, 1)

    oFieldtime = ogr.FieldDefn("duration", ogr.OFTInteger)
    shapLayer.CreateField(oFieldtime, 1)

    oDefn = shapLayer.GetLayerDefn()
    feature = ogr.Feature(oDefn)
    for line in data:
        # 字段赋值
        feature.SetField(0, line[0])
        feature.SetField(1, line[1])
        feature.SetField(2, line[2])
        feature.SetField(3, line[3])
        feature.SetField(4, line[4])
        feature.SetField(5, line[5])
        # 创建线类数据
        line_f = ogr.Geometry(ogr.wkbLineString25D)
        features = line[-1].split(' ')
        # 添加线位置属性
        for one in features:
            if len(one) > 3:
                xyt = one.split(',')
                x = float(xyt[0])
                y = float(xyt[1])
                t = (int(xyt[2]) - 1448380800) / 86400.0
                line_f.AddPoint(x, y, t)

        feature.SetGeometry(line_f)
        shapLayer.CreateFeature(feature)
    feature.Destroy()
    ds.Destroy()


if __name__ == '__main__':
    path = r'K:\show.txt'
    # path =r'E:\python\beijingdidi_show\test.txt'
    data = read_data(path)
    createShap(data)
