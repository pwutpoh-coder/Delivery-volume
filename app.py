import urllib.parse
import pandas as pd
import plotly.express as px
import streamlit as st

# ตั้งค่าหน้าเว็บแดชบอร์ด
st.set_page_config(
    page_title="Dashboard ยอดส่งระหว่างเดือน", page_icon="📊", layout="wide"
)

# Custom CSS ตกแต่งโทนสีพาสเทล น้ำเงิน ฟ้า ขาว สบายตา
st.markdown(
    """
    <style>
    .main {
        background-color: #F8FAFC;
    }
    .stButton>button {
        background-color: #3B82F6;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2563EB;
        color: white;
    }
    div.stMetric {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 5px solid #3B82F6;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📊 แดชบอร์ดวิเคราะห์ยอดส่งระหว่างเดือน (Cross-Filter Dashboard)")
st.markdown(
    "ระบบวิเคราะห์ข้อมูลจาก Google Sheets ครอบคลุมทุกมุมมอง พร้อมระบบกรองข้อมูลข้ามกลุ่ม"
)


# 1. ฟังก์ชันโหลดข้อมูลแบบครอบคลุมทุกแถวและคอลัมน์
@st.cache_data(ttl=60)
def load_data():
  sheet_id = "1XRkHwEJoEPiVVortmkN60mN39TSsHN2JVo733US3fQs"
  sheet_name_encoded = urllib.parse.quote("ยอดส่งระหว่างเดือน")
  url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}"
  try:
    df = pd.read_csv(url)
    return df
  except Exception as e:
    # Fallback กรณีดึงชื่อชีทไม่ผ่าน
    url_fallback = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(url_fallback)
    return df


# โหลดข้อมูล
df_raw = load_data()

if df_raw.empty:
  st.error(
      "ไม่พบข้อมูลใน Google Sheets กรุณาตรวจสอบลิงก์หรือสิทธิ์การเข้าถึงอีกครั้ง"
  )
else:
  # ทำความสะอาดชื่อคอลัมน์
  df_raw.columns = df_raw.columns.astype(str).str.strip()

  # จัดการ Session State สำหรับระบบ Cross-Filter
  if "selected_filters" not in st.session_state:
    st.session_state.selected_filters = {}

  # Sidebar: ปุ่มรีเซ็ตข้อมูลทั้งหมด
  st.sidebar.header("🎛️ ตัวควบคุมแดชบอร์ด")
  if st.sidebar.button("🔄 รีเซ็ตตัวกรองทั้งหมด (Reset Filters)"):
    st.session_state.selected_filters = {}
    st.rerun()

  # คัดแยกคอลัมน์สำหรับทำกราฟ (บังคับให้ดึงคอลัมน์ที่มีข้อมูลมาใช้ได้ทันที)
  all_columns = df_raw.columns.tolist()

  # เลือกคอลัมน์มาแสดง 3 มิติสำหรับ กราฟวงกลม, กราฟแท่ง, กราฟเส้น (ถ้าคอลัมน์ไม่พอให้ใช้ซ้ำได้)
  col_pie = all_columns[0] if len(all_columns) > 0 else None
  col_bar = all_columns[1] if len(all_columns) > 1 else col_pie
  col_line = all_columns[2] if len(all_columns) > 2 else col_bar

  # กรองข้อมูลตาม State ที่ถูกเลือกข้ามกลุ่ม
  filtered_df = df_raw.copy()
  for col, val_list in st.session_state.selected_filters.items():
    if val_list and col in filtered_df.columns:
      filtered_df = filtered_df[filtered_df[col].isin(val_list)]

  # แสดง Metric ภาพรวมด้านบน
  m1, m2, m3, m4 = st.columns(4)
  with m1:
    st.metric("📦 จำนวนรายการทั้งหมด", f"{len(filtered_df):,}")
  with m2:
    num_cols = filtered_df.select_dtypes(
        include=["float64", "int64"]
    ).columns.tolist()
    if num_cols:
      total_sum = filtered_df[num_cols[0]].sum()
      st.metric(f"💰 รวม ({num_cols[0]})", f"{total_sum:,.2f}")
    else:
      st.metric("💰 ยอดรวม", f"{len(filtered_df):,}")
  with m3:
    ratio_pct = (
        (len(filtered_df) / len(df_raw) * 100) if len(df_raw) > 0 else 0
    )
    st.metric("📈 สัดส่วนข้อมูลที่แสดง", f"{ratio_pct:.1f}%")
  with m4:
    st.metric("🔗 เงื่อนไข Cross-Filter", f"{len(st.session_state.selected_filters)} มิติ")

  st.markdown("---")
  st.markdown(
      "💡 *คำแนะนำ: สามารถคลิกที่ชิ้นส่วนกราฟด้านล่าง เพื่อกรองข้อมูลข้ามกลุ่มไปยังกราฟอื่นๆ และตารางได้ทันที*"
  )

  # แสดงผล 3 กราฟใน 3 มุมมอง (วงกลม, แท่ง, เส้น)
  g1, g2, g3 = st.columns(3)

  # --- 1. กราฟวงกลม (Pie Chart) ---
  with g1:
    st.subheader(f"🌐 1. สัดส่วน: {col_pie}")
    if col_pie:
      pie_data = (
          filtered_df[col_pie].astype(str).value_counts().reset_index().head(8)
      )
      pie_data.columns = [col_pie, "count"]

      fig_pie = px.pie(
          pie_data,
          names=col_pie,
          values="count",
          hole=0.4,
          color_discrete_sequence=px.colors.sequential.Blues_r,
      )
      fig_pie.update_layout(
          margin=dict(t=20, b=20, l=20, r=20),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
      )

      selected_pie = st.plotly_chart(
          fig_pie, use_container_width=True, key="pie_chart", on_select="rerun"
      )

      if (
          selected_pie
          and "selection" in selected_pie
          and selected_pie["selection"]["points"]
      ):
        selected_points = [
            p["label"] for p in selected_pie["selection"]["points"]
        ]
        st.session_state.selected_filters[col_pie] = selected_points
        st.rerun()

  # --- 2. กราฟแท่ง (Bar Chart) ---
  with g2:
    st.subheader(f"📊 2. เปรียบเทียบ: {col_bar}")
    if col_bar:
      bar_data = (
          filtered_df[col_bar].astype(str).value_counts().reset_index().head(10)
      )
      bar_data.columns = [col_bar, "count"]

      fig_bar = px.bar(
          bar_data,
          x=col_bar,
          y="count",
          text="count",
          color="count",
          color_continuous_scale="Blues",
      )
      fig_bar.update_layout(
          margin=dict(t=20, b=20, l=20, r=20),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
          coloraxis_showscale=False,
      )

      selected_bar = st.plotly_chart(
          fig_bar, use_container_width=True, key="bar_chart", on_select="rerun"
      )

      if (
          selected_bar
          and "selection" in selected_bar
          and selected_bar["selection"]["points"]
      ):
        selected_points = [p["x"] for p in selected_bar["selection"]["points"]]
        st.session_state.selected_filters[col_bar] = selected_points
        st.rerun()

  # --- 3. กราฟเส้น (Line Chart) ---
  with g3:
    st.subheader(f"📈 3. แนวโน้ม: {col_line}")
    if col_line:
      line_data = (
          filtered_df[col_line].astype(str).value_counts().reset_index().head(12)
      )
      line_data.columns = [col_line, "count"]
      line_data = line_data.sort_values(by=col_line)

      fig_line = px.line(
          line_data,
          x=col_line,
          y="count",
          markers=True,
          color_discrete_sequence=["#2563EB"],
      )
      fig_line.update_layout(
          margin=dict(t=20, b=20, l=20, r=20),
          paper_bgcolor="rgba(0,0,0,0)",
          plot_bgcolor="rgba(0,0,0,0)",
      )

      selected_line = st.plotly_chart(
          fig_line, use_container_width=True, key="line_chart", on_select="rerun"
      )

      if (
          selected_line
          and "selection" in selected_line
          and selected_line["selection"]["points"]
      ):
        selected_points = [p["x"] for p in selected_line["selection"]["points"]]
        st.session_state.selected_filters[col_line] = selected_points
        st.rerun()

  st.markdown("---")

  # แสดงตารางข้อมูลรายละเอียดทั้งหมดที่ผ่านการกรองแล้ว
  st.subheader("📋 ตารางข้อมูลรายละเอียด (Filtered Data)")
  st.dataframe(filtered_df, use_container_width=True)

  # ปุ่มดาวน์โหลดข้อมูล
  csv_export = filtered_df.to_csv(index=False).encode("utf-8-sig")
  st.download_button(
      label="📥 ดาวน์โหลดข้อมูล (.csv)",
      data=csv_export,
      file_name="filtered_data.csv",
      mime="text/csv",
  )
