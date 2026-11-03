/**
 * 首页表单交互逻辑
 * - 表单直接提交 → target="_blank" 在新标签页打开海报
 * - 按钮 Loading 状态
 * - PostMessage 接收海报页回调，自动恢复按钮
 */
document.addEventListener("DOMContentLoaded", () => {
    const form       = document.getElementById("generateForm");
    const btn        = document.getElementById("btnGenerate");
    const btnText    = btn.querySelector(".btn-text");
    const btnLoading = btn.querySelector(".btn-loading");
    const errorMsg   = document.getElementById("errorMsg");

    form.addEventListener("submit", (e) => {
        // 简单校验
        const payload = {
            grade:      document.getElementById("grade").value,
            subject:    document.getElementById("subject").value,
            stage:      document.getElementById("stage").value,
            book:       document.getElementById("book").value,
            publisher:  document.getElementById("publisher").value,
            unit_name:  document.getElementById("unit_name").value.trim()
        };

        for (const [key, val] of Object.entries(payload)) {
            if (!val) {
                e.preventDefault();
                showError("请填写所有字段后再提交！");
                return;
            }
        }

        // 校验通过，进入 Loading 状态
        setLoading(true);
        hideError();
        // 表单会自动提交到 action="/generate" target="_blank"
    });

    /* ---------- 工具函数 ---------- */

    function setLoading(isLoading) {
        btn.disabled = isLoading;
        btnText.style.display    = isLoading ? "none"   : "inline";
        btnLoading.style.display = isLoading ? "inline" : "none";
    }

    function showError(msg) {
        errorMsg.textContent = "❌ " + msg;
        errorMsg.style.display = "block";
    }

    function hideError() {
        errorMsg.style.display = "none";
    }

    /* ---------- 2026-05-14: localStorage storage 事件回调 ----------
     * 监听来自新标签页海报的 localStorage 变化
     * 海报加载完成后会写入 poster_ready_<timestamp>，收到后恢复按钮
     */
    window.addEventListener("storage", (event) => {
        if (event.key && event.key.startsWith("poster_ready_")) {
            setLoading(false);  // 恢复按钮
            console.log("[首页] 收到海报加载完成通知 (localStorage)，按钮已恢复");
        }
    });
});
