#!/usr/bin/env python
"""诊断坐标定位问题"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from app.services.amap_service import get_amap_service
from app.models.schemas import TripRequest


def diagnose_coordinates():
    """诊断坐标问题"""
    print("\n" + "=" * 70)
    print("坐标定位问题诊断工具")
    print("=" * 70 + "\n")
    
    try:
        service = get_amap_service()
        
        # 测试城市 - 厦门
        test_city = "厦门"
        
        print(f"📍 正在测试 {test_city} 的坐标...")
        print("-" * 70 + "\n")
        
        # 测试1: 搜索景点
        print("🔍 测试1: 景点搜索坐标")
        attractions = service.search_poi("景点", test_city, citylimit=True)
        
        if attractions:
            print(f"找到 {len(attractions)} 个景点\n")
            for i, attr in enumerate(attractions[:5], 1):
                print(f"{i}. {attr.name}")
                print(f"   ID: {attr.id}")
                print(f"   地址: {attr.address}")
                print(f"   坐标: ({attr.location.longitude}, {attr.location.latitude})")
                
                # 检查坐标有效性
                lng = attr.location.longitude
                lat = attr.location.latitude
                
                # 厦门的大致坐标范围
                in_range = 117.5 <= lng <= 118.5 and 24.0 <= lat <= 24.8
                status = "✅" if in_range else "❌"
                print(f"   有效性: {status} ({'在厦门范围内' if in_range else '超出厦门范围'})")
                print()
        else:
            print("❌ 未找到景点\n")
        
        # 测试2: 地理编码
        print("\n🔍 测试2: 地理编码坐标")
        location = service.geocode(f"{test_city}市", test_city)
        if location:
            print(f"城市坐标: ({location.longitude}, {location.latitude})")
            lng = location.longitude
            lat = location.latitude
            in_range = 117.5 <= lng <= 118.5 and 24.0 <= lat <= 24.8
            print(f"有效性: {'✅' if in_range else '❌'} ({'在厦门范围内' if in_range else '超出厦门范围'})")
        else:
            print("❌ 地理编码失败")
        
        # 测试4: 坐标格式检查
        print("\n🔍 测试3: 坐标格式检查")
        print("高德 API 返回格式: 'longitude,latitude'")
        print("Location 模型格式: {longitude: float, latitude: float}")
        print("前端高德地图格式: [longitude, latitude]")
        
        if attractions:
            first = attractions[0]
            print(f"\n示例坐标:")
            print(f"  原始字符串: (模拟) '117.956,24.429'")
            print(f"  解析后: longitude={first.location.longitude}, latitude={first.location.latitude}")
            print(f"  前端使用: [{first.location.longitude}, {first.location.latitude}]")
        
        # 测试5: 多个景点坐标间距检查
        print("\n🔍 测试4: 景点坐标分布")
        if len(attractions) >= 2:
            print(f"检查前5个景点的坐标分布:\n")
            for i in range(min(5, len(attractions))):
                attr = attractions[i]
                print(f"  {i+1}. {attr.name}: ({attr.location.longitude:.4f}, {attr.location.latitude:.4f})")
            
            # 计算坐标分布范围
            lngs = [attr.location.longitude for attr in attractions[:5]]
            lats = [attr.location.latitude for attr in attractions[:5]]
            
            print(f"\n坐标范围:")
            print(f"  经度: {min(lngs):.4f} ~ {max(lngs):.4f} (差异: {max(lngs)-min(lngs):.4f})")
            print(f"  纬度: {min(lats):.4f} ~ {max(lats):.4f} (差异: {max(lats)-min(lats):.4f})")
            
            if max(lngs) - min(lngs) < 0.001 or max(lats) - min(lats) < 0.001:
                print(f"  ⚠️  警告: 景点分布过于集中,可能存在坐标重复或错误")
        
        # 新增: 测试景点名称匹配
        print("\n🔍 测试5: 景点名称匹配模拟")
        print("这模拟 LLM 生成的景点与实际搜索结果的匹配情况:\n")
        
        llm_generated_names = ["鼓浪屿", "中山路步行街", "白鹭洲", "厦门园林植物园", "南普陀寺"]
        real_names = {attr.name for attr in attractions}
        
        print(f"搜索到的景点({len(real_names)}个):")
        for i, name in enumerate(list(real_names)[:5], 1):
            print(f"  {i}. {name}")
        
        print(f"\nLLM可能生成的景点:")
        matches = []
        for i, llm_name in enumerate(llm_generated_names, 1):
            # 检查是否存在相同或相似的景点
            found = None
            for real_attr in attractions:
                if llm_name in real_attr.name or real_attr.name in llm_name:
                    found = real_attr
                    break
            
            if found:
                matches.append(True)
                print(f"  {i}. ✅ '{llm_name}' → 匹配到 '{found.name}'")
            else:
                matches.append(False)
                # 用第一个搜索结果替代
                print(f"  {i}. ❌ '{llm_name}' → 未匹配，将使用第{i}个搜索结果 '{attractions[i-1].name if i-1 < len(attractions) else 'N/A'}'")
        
        match_rate = sum(matches) / len(matches) * 100
        print(f"\n匹配率: {match_rate:.1f}%")
        if match_rate < 100:
            print("⚠️  提示: 低匹配率可能导致地址与坐标组合不对")
        
        print("\n" + "=" * 70)
        print("诊断完成")
        print("=" * 70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ 诊断失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = diagnose_coordinates()
    sys.exit(0 if success else 1)
