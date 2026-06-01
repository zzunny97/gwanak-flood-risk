import pandas as pd
import geopandas as gpd

print("=" * 70)
print("1. 쇠퇴진단지표 (decline_sigungu.csv)")
print("=" * 70)
df = pd.read_csv("decline_sigungu.csv", encoding="cp949")
print(f"shape: {df.shape}")
print(f"columns ({len(df.columns)}):")
for c in df.columns:
    print(f"  - {c}")
print("\nhead:")
print(df.head(3).to_string())
print(f"\n연도 분포: {df.iloc[:, 0].unique() if df.shape[1] else 'N/A'}")

print("\n" + "=" * 70)
print("2. 활성화지역 진단지표 (activate_sigungu.csv)")
print("=" * 70)
df2 = pd.read_csv("activate_sigungu.csv", encoding="cp949")
print(f"shape: {df2.shape}")
print(f"columns ({len(df2.columns)}):")
for c in df2.columns:
    print(f"  - {c}")
print("\nhead:")
print(df2.head(3).to_string())

print("\n" + "=" * 70)
print("3. 잠재력 지표 (potential_sigungu.csv)")
print("=" * 70)
df3 = pd.read_csv("potential_sigungu.csv", encoding="cp949")
print(f"shape: {df3.shape}")
print(f"columns ({len(df3.columns)}):")
for c in df3.columns:
    print(f"  - {c}")
print("\nhead:")
print(df3.head(3).to_string())

print("\n" + "=" * 70)
print("4. 행정동 GeoJSON (admdong.geojson)")
print("=" * 70)
gdf = gpd.read_file("admdong.geojson")
print(f"shape: {gdf.shape}")
print(f"CRS: {gdf.crs}")
print(f"columns: {list(gdf.columns)}")
print("\nhead:")
print(gdf.head(3).to_string())
