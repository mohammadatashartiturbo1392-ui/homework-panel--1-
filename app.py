import streamlit as st
from supabase import create_client
import base64
from PIL import Image
import io

# --- تنظیمات اتصال اختصاصی شما ---
SUPABASE_URL = "https://bpglbgtoxutwpsuupjxv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwZ2xiZ3RveHV0d3BzdXVwanh2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA3MzIzNjAsImV4cCI6MjA4NjMwODM2MH0.qzXalKXxqyqZFw-Arb8YhsMt_L6ShE-RdYI8pRYyTOc"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- توابع مدیریت داده (Supabase) ---
def load_data():
    try:
        res = supabase.table("homework_data").select("*").execute()
        return {row['teacher_name']: {"password": row['teacher_password'], "assignments": row['data']} for row in res.data}
    except Exception as e:
        st.error(f"خطا در بارگذاری: {e}")
        return {}

def save_to_supabase(t_name, t_pass, t_data):
    check = supabase.table("homework_data").select("id").eq("teacher_name", t_name).execute()
    payload = {"teacher_name": t_name, "teacher_password": t_pass, "data": t_data}
    if check.data:
        supabase.table("homework_data").update({"data": t_data}).eq("teacher_name", t_name).execute()
    else:
        supabase.table("homework_data").insert(payload).execute()

def process_image(uploaded_file):
    img = Image.open(uploaded_file)
    img.thumbnail((800, 800)) 
    buffer = io.BytesIO()
    # تبدیل به RGB برای اطمینان از فرمت JPEG
    img.convert("RGB").save(buffer, format="JPEG", quality=50) 
    return base64.b64encode(buffer.getvalue()).decode()

# --- ظاهر برنامه ---
st.set_page_config(page_title="پنل تکالیف هوشمند", layout="wide")
data = load_data()

menu = st.sidebar.radio("منو", ["🏠 خانه", "📤 ارسال تکلیف", "🔍 پیگیری نمره", "👨‍🏫 پنل معلم"])

if menu == "🏠 خانه":
    st.title("📚 سامانه مدیریت تکالیف")
    st.success("ارتباط با دیتابیس سوپابیس برقرار است ✅")
    st.write("معلمین عزیز ابتدا در پنل خود ثبت‌نام و تکلیف تعریف کنند.")

elif menu == "📤 ارسال تکلیف":
    st.header("ارسال توسط دانش‌آموز")
    teachers = list(data.keys())
    if not teachers:
        st.warning("ابتدا باید یک معلم ثبت‌نام کند.")
    else:
        t_name = st.selectbox("انتخاب معلم", teachers)
        asgns = data[t_name]["assignments"]
        if not asgns:
            st.info("تکلیفی تعریف نشده است.")
        else:
            asgn_id = st.selectbox("انتخاب تکلیف", list(asgns.keys()), format_func=lambda x: asgns[x]["title"])
            s_name = st.text_input("نام دانش‌آموز")
            files = st.file_uploader("آپلود عکس‌ها", accept_multiple_files=True, type=['jpg','jpeg','png'])
            
            if st.button("ارسال نهایی"):
                if s_name and files:
                    with st.spinner("در حال ارسال عکس‌ها..."):
                        img_list = [process_image(f) for f in files]
                        data[t_name]["assignments"][asgn_id]["submissions"][s_name] = {
                            "images": img_list, "grade": "", "feedback": "", "status": "ارسال شده"
                        }
                        save_to_supabase(t_name, data[t_name]["password"], data[t_name]["assignments"])
                        st.success("ارسال با موفقیت انجام شد!")
                else:
                    st.error("نام و عکس الزامی است.")

elif menu == "🔍 پیگیری نمره":
    st.header("پیگیری وضعیت")
    q_name = st.text_input("نام خود را وارد کنید")
    if st.button("جستجو"):
        found = False
        for t_name, t_info in data.items():
            for a_id, a_info in t_info["assignments"].items():
                if q_name in a_info["submissions"]:
                    sub = a_info["submissions"][q_name]
                    st.info(f"تکلیف: {a_info['title']} | معلم: {t_name}")
                    st.write(f"**نمره:** {sub['grade'] if sub['grade'] else 'تصحیح نشده'}")
                    st.write(f"**بازخورد:** {sub['feedback']}")
                    found = True
        if not found: st.error("یافت نشد.")

elif menu == "👨‍🏫 پنل معلم":
    st.header("مدیریت معلم")
    user = st.text_input("نام کاربری")
    pw = st.text_input("رمز عبور", type="password")
    
    if st.button("ورود / ثبت‌نام"):
        if user not in data:
            save_to_supabase(user, pw, {})
            st.success("حساب کاربری معلم ساخته شد. دوباره دکمه را بزنید.")
            st.rerun()
        elif data[user]["password"] == pw:
            st.session_state["teacher"] = user
            st.success("وارد شدید!")
        else:
            st.error("رمز اشتباه است.")

    if "teacher" in st.session_state:
        t_user = st.session_state["teacher"]
        st.divider()
        tab1, tab2 = st.tabs(["➕ تعریف تکلیف", "📝 تصحیح"])
        
        with tab1:
            title = st.text_input("عنوان تکلیف (مثلاً ریاضی ص ۱۰)")
            if st.button("ثبت تکلیف"):
                new_id = str(len(data[t_user]["assignments"]) + 1)
                data[t_user]["assignments"][new_id] = {"title": title, "submissions": {}}
                save_to_supabase(t_user, data[t_user]["password"], data[t_user]["assignments"])
                st.success("تکلیف با موفقیت ساخته شد.")
                st.rerun()
        
        with tab2:
            asgns = data[t_user]["assignments"]
            if asgns:
                sel_id = st.selectbox("تکلیف را انتخاب کنید", list(asgns.keys()), format_func=lambda x: asgns[x]["title"])
                subs = asgns[sel_id]["submissions"]
                for s_name, s_info in subs.items():
                    with st.expander(f"👤 {s_name}"):
                        for img_str in s_info["images"]:
                            st.image(base64.b64decode(img_str), width=400)
                        g = st.text_input(f"نمره {s_name}", value=s_info["grade"], key=f"g{s_name}")
                        f = st.text_area(f"بازخورد {s_name}", value=s_info["feedback"], key=f"f{s_name}")
                        if st.button(f"ذخیره برای {s_name}", key=f"b{s_name}"):
                            data[t_user]["assignments"][sel_id]["submissions"][s_name].update({"grade": g, "feedback": f})
                            save_to_supabase(t_user, data[t_user]["password"], data[t_user]["assignments"])
                            st.success("ثبت شد.")