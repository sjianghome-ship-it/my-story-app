import streamlit as st
import requests
import time
import random
import os
from streamlit_mic_recorder import mic_recorder # 导入语音组件

# -----------------------------------------------------------------
# 核心配置：API URL
# -----------------------------------------------------------------
# 🚨 替换为您在 Colab 单元格 #3 中获得的实际公共 URL！
COLAB_API_BASE_URL = "https://5000-m-s-kkb-usw1c1-2rz4n56h1mgvq-c.us-west1-1.sandbox.colab.dev" 
API_ENDPOINT_SCRIPT = COLAB_API_BASE_URL + "/generate_script"       # 终点：生成短文
API_ENDPOINT_QUESTION = COLAB_API_BASE_URL + "/get_next_question"   # 终点：生成问题

# -----------------------------------------------------------------
# 核心对话配置 (简化为无主题模式)
# -----------------------------------------------------------------
STARTER_PROMPT = "嗨，朋友！今天有啥可以唠唠的？是开心还是烦恼，先来聊个五块钱的！"
AI_ROLE = "全能故事陪聊官"
AI_ICON = "🍻"


# -----------------------------------------------------------------
# 核心函数：调用 Colab 后端 API (通用化)
# -----------------------------------------------------------------
def call_colab_api(chat_messages, endpoint_url):
    """
    将聊天记录发送到 Colab 后端 API，并接收 JSON 响应。
    endpoint_url: 可以是 API_ENDPOINT_SCRIPT 或 API_ENDPOINT_QUESTION
    """
    
    # 格式化聊天记录为后端需要的列表 ["角色: 内容", ...]
    formatted_history = [f"{msg['role']}: {msg['content']}" 
                         for msg in chat_messages 
                         if msg['role'] in ('user', 'assistant')]
    
    payload = {
        "chat_history": formatted_history
    }
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(endpoint_url, json=payload, headers=headers, timeout=60) 
        response.raise_for_status() # 检查 HTTP 错误 (4xx 或 5xx)
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"API 通信错误: {e}"}


# -----------------------------------------------------------------
# Streamlit UI 配置和流程
# -----------------------------------------------------------------
st.set_page_config(page_title="故事酿造机", layout="centered")
st.title("🎙️ 故事酿造机：你有故事，我有酒")
st.caption("通过语音或文本输入，将经历转化为爆款短文/段子。")

# -----------------------------------------------------------------
# 核心初始化逻辑 (最精简、最稳定版本)
# -----------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 首次加载时，添加 AI 的开场白
    st.session_state.messages.append({"role": "assistant", "content": STARTER_PROMPT})


# -----------------------------------------------------------------
# 聊天历史记录显示
# -----------------------------------------------------------------
for message in st.session_state.messages:
    # 使用 AI_ROLE 作为助手的名称
    role_name = AI_ROLE if message["role"] == "assistant" else "user"
    with st.chat_message(role_name):
        st.markdown(message["content"])


# -----------------------------------------------------------------
# 用户输入处理：语音输入组件与文本输入 (增强错误处理)
# -----------------------------------------------------------------
st.subheader(f"🎤 {AI_ICON} 讲出你的故事...")

# 麦克风组件
audio_info = mic_recorder(
    start_prompt="点击开始录音",
    stop_prompt="点击停止，AI 正在转录...",
    key='mic_input',
    just_once=True,
    use_container_width=True,
    format="webm"
)

# 初始化 prompt 变量
prompt = None

# 1. 处理语音输入
if audio_info:
    if 'text' in audio_info and audio_info['text']:
        # 成功转录
        st.session_state['transcribed_text'] = audio_info['text']
    elif 'audio_data' in audio_info and audio_info['audio_data']:
        # 录音成功，但转录失败
        st.session_state['transcribed_text'] = "⚠️ 语音转录失败，请手动编辑或输入文本。"
        st.warning("⚠️ 语音转录失败，请手动编辑或检查浏览器权限/网络。")

# 2. 显示可编辑的转录文本和确认按钮
if 'transcribed_text' in st.session_state and st.session_state['transcribed_text']:
    st.session_state['transcribed_text'] = st.text_area(
        "🎙️ 你的故事 (可编辑，点击确认发送):", 
        value=st.session_state['transcribed_text'], 
        key='current_story_input_area'
    )
    if st.button("✅ 确认发送故事"):
        prompt = st.session_state['transcribed_text']
        # 清除状态，防止重复发送
        del st.session_state['transcribed_text']
    
# 3. 文本备用输入 (如果用户想手动输入，且没有等待确认的转录文本)
if not prompt and 'transcribed_text' not in st.session_state:
    prompt = st.chat_input("或在这里输入故事文本...", key='text_fallback_input')


# -----------------------------------------------------------------
# 主逻辑处理 (用户点击确认或文本回车后触发)
# -----------------------------------------------------------------
if prompt:
    # 1. 记录并显示用户输入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用 Colab 后端 API 获取下一个问题 (实时调用！)
    with st.chat_message(AI_ROLE):
        with st.spinner(f"{AI_ROLE} 正在为你斟酒，并思考下一个问题..."):
            
            # --- 调用新的 API 端点: /get_next_question ---
            question_response = call_colab_api(st.session_state.messages, 
                                               endpoint_url=API_ENDPOINT_QUESTION)
            
            if question_response['success']:
                # 确保模型返回的是纯文本，不是Markdown或其他格式
                assistant_text = question_response.get('next_question', '请多说一些细节。')
                st.markdown(assistant_text)
                st.session_state.messages.append({"role": "assistant", "content": assistant_text})
                
            else:
                st.error(f"AI 问答失败: {question_response['error']}")
                # 备用 MOCK 回复，防止 API 失败导致流程中断
                backup_mock = "嗯，听起来很有意思！不过咱们再深入一点，这件事的转折点是什么？（系统 API 暂时故障，请稍后再试或继续打字）"
                st.markdown(backup_mock)
                st.session_state.messages.append({"role": "assistant", "content": backup_mock})


# -----------------------------------------------------------------
# 脚本生成按钮 (调用核心 API)
# -----------------------------------------------------------------
if st.button("✨ 立即生成爆款短文"):
    if len(st.session_state.messages) < 3:
        st.warning("请至少进行两轮对话，确保故事细节足够丰富！")
    else:
        st.info("正在发送完整的聊天记录到云端后端，酿造最终爆款短文...")
        
        with st.spinner("⏳ 爆款短文/段子酿造中...这可能需要 10-20 秒。"):
            
            # --- 调用最终生成 API 端点: /generate_script ---
            final_script_response = call_colab_api(st.session_state.messages, 
                                                  endpoint_url=API_ENDPOINT_SCRIPT)
            
            if final_script_response['success']:
                st.balloons()
                st.success("🎉 爆款短文成功出炉！")
                st.markdown("---")
                st.code(final_script_response['script'], language='markdown') 
            else:
                st.error(f"短文生成失败: {final_script_response['error']}")
                st.info(f"详细信息: {final_script_response.get('details', '请确保 Colab 仍在运行，且 API URL 设置正确！')}")
