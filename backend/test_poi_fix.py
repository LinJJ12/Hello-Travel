#!/usr/bin/env python
"""测试POI搜索修复"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from app.services.amap_service import get_amap_service
from app.models.schemas import POIInfo


def test_poi_search():
    """测试POI搜索"""
    print("=" * 60)
    print("测试 POI 搜索修复")
    print("=" * 60 + "\n")
    
    try:
        service = get_amap_service()
        
        # 测试1: 搜索景点
        print("📍 测试1: 搜索景点...")
        attractions = service.search_poi("景点", "厦门", citylimit=True)
        print(f"✅ 景点搜索结果: {len(attractions)} 个")
        for i, attr in enumerate(attractions[:3], 1):
            print(f"   {i}. {attr.name}")
            print(f"      位置: ({attr.location.longitude}, {attr.location.latitude})")
            print(f"      电话: {attr.tel}")
        print()
        
        # 测试2: 搜索酒店
        print("🏨 测试2: 搜索酒店...")
        hotels = service.search_poi("酒店", "厦门", citylimit=True)
        print(f"✅ 酒店搜索结果: {len(hotels)} 个")
        for i, hotel in enumerate(hotels[:3], 1):
            print(f"   {i}. {hotel.name}")
            print(f"      位置: ({hotel.location.longitude}, {hotel.location.latitude})")
        print()
        
        # 测试3: 天气查询
        print("🌤️  测试3: 天气查询...")
        weather = service.get_weather("厦门")
        print(f"✅ 天气查询结果: {len(weather)} 天")
        for i, w in enumerate(weather[:3], 1):
            print(f"   {i}. {w.date}: {w.day_weather} {w.day_temp}°C")
        print()
        
        print("=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_poi_search()
