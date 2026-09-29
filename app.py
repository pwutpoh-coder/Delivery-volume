import urllib.parse
import pandas as pd
import plotly.express as px
import streamlit as st

# ตั้งค่าหน้าเว็บแดชบอร์ด
st.set_page_config(
    page_title="Dashboard ยอดส่งระหว่างเดือน", page_icon="📊", layout="wide"
)

st.title("📊 แดชบอร์ดวิเคราะห์ยอดส่งระหว่างเดือน")
st.markdown(
    "ระบบกรองข้อมูลแบบ Multi-dimensional Cross-filtering เชื่อมต่อข้อมูลจาก Google Sheets แบบเรียลไทม์"
)

# ฟังก์ชันโหลดข้อมูลจาก Google Sheets โดยดึงเฉพาะชีท "ยอดส่งระหว่างเดือน"


@st.cache_data(ttl=300)
def load_data():
  sheet_id = "1XRkHwEJoEPiVVortmkN60mN39TSsHN2JVo733US3fQs"
  sheet_name_encoded = urllib.parse.quote("ยอดส่งระหว่างเดือน")
  url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}"
  df = pd.read_csv(url)
  return df


# โหลดข้อมูล
try:
  df = load_data()
except Exception as e:
  st.error(
      f"ไม่สามารถดึงข้อมูลจาก Google Sheets ได้ กรุณาตรวจสอบชื่อชีท 'ยอดส่งระหว่างเดือน' และสิทธิ์การแชร์ลิงก์: {e}"
  )
  df = pd.DataFrame()

if not df.empty:
  # ทำความสะอาดชื่อคอลัมน์ (ตัดช่องว่างถ้ามี)
  df.columns = df.columns.str.strip()

  # Sidebar: ตัวกรองข้อมูลทุกมิติ (Global Cross-Filters)
  st.sidebar.header("🔍 ตัวกรองข้อมูล (Filters)")

  filtered_df = df.copy()

  # ค้นหาคอลัมน์ที่เกี่ยวกับสถานะหรือดราฟอัตโนมัติ
  draft_cols = [
      c for c in df.columns if "ดราฟ" in c or "Status" in c or "สถานะ" in c
  ]
  if draft_cols:
    selected_draft = st.sidebar.multiselect(
        "📌 กองสถานะ / ดราฟ", options=df[draft_cols[0]].dropna().unique()
    )
    if selected_draft:
      filtered_df = filtered_df[filtered_df[draft_cols[0]].isin(selected_draft)]

  # ค้นหาคอลัมน์ประเภทข้อความ/หมวดหมู่สำหรับทำฟิลเตอร์ข้ามกลุ่ม
  cat_cols = [
      c
      for c in df.columns
      if df[c].dtype == "object"
      and c not in draft_cols
      and len(df[c].unique()) < 100
  ]

  selected_filters = {}
  for col in cat_cols[:5]:  # เลือกมา 5 มิติหลักแรก
    options = df[col].dropna().unique().tolist()
    selected = st.sidebar.multiselect(f"📂 เลือก {col}", options=options)
    if selected:
      filtered_df = filtered_df[filtered_df[col].isin(selected)]

  # ส่วนแสดงผล Metric Summary ด้านบน
  st.markdown("---")
  m1, m2, m3, m4 = st.columns(4)
  with m1:
    st.metric("จำนวนรายการทั้งหมด", f"{len(filtered_df):,}")
  with m2:
    # หาคอลัมน์ที่เป็นตัวเลข (เช่น จำนวนเงิน, น้ำหนัก, จำนวนชิ้น)
    num_cols = df.select_dtypes(include=["float64", "int64"]).columns.tolist()
    if num_cols:
      total_val = filtered_df[num_cols[0]].sum()
      st.metric(f"รวม {num_cols[0]}", f"{total_val:,.2f}")
    else:
      st.metric("ยอดรวม", "-")
  with m3:
    pct = (
        (len(filtered_df) / len(df) * 100)
        if len(df) > 0
        else 0
    )
    st.metric("สัดส่วนจากข้อมูลทั้งหมด", f"{pct:.1f}%")
  with m4:
    st.metric("จำนวนเงื่อนไขที่กรอง", f"{len(selected_filters)} ตัวกรอง")

  # ส่วนกราฟวิเคราะห์ข้อมูลข้ามมิติ
  st.markdown("### 📈 กราฟสรุปผลตามมิติข้อมูล")
  g1, g2 = st.columns(2)

  if len(cat_cols) >= 1 and not filtered_df.empty:
    with g1:
      fig_pie = px.pie(
          filtered_df,
          names=cat_cols[0],
          title=f"สัดส่วนแยกตาม {cat_cols[0]}",
          hole=0.4,
      )
      st.plotly_chart(fig_pie, use_container_width=True)

  if len(cat_cols) >= 2 and not filtered_df.empty:
    with g2:
      val_counts = (
          filtered_df[cat_cols[1]].value_counts().reset_index().head(10)
      )
      val_counts.columns = [cat_cols[1], "count"]
      fig_bar = px.bar(
          val_counts,
          x=cat_cols[1],
          y="count",
          title=f"10 อันดับสูงสุดตาม {cat_cols[1]}",
          text="count",
      )
      st.plotly_chart(fig_bar, use_container_width=True)

  # ส่วนตารางแสดงข้อมูลรายละเอียด
  st.markdown("### 📋 ตารางข้อมูลรายละเอียด (Filtered Data Table)")
  st.dataframe(filtered_df, use_container_width=True)

  # ปุ่มดาวน์โหลดข้อมูลที่ผ่านการกรองแล้ว
  csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
  st.download_button(
      label="📥 ดาวน์โหลดข้อมูลที่กรองแล้ว (.csv)",
      data=csv_data,
      file_name="filtered_delivery_report.csv",
      mime="text/csv",
  )
else:
  st.info("ไม่พบข้อมูลในชีท กรุณาตรวจสอบรูปแบบไฟล์ Google Sheets อีกครั้ง")
