// 通用 JavaScript 腳本
console.log("主腳本已載入。");

// 可以在這裡加入全站共用的互動效果，例如 Tooltip 初始化等
document.addEventListener('DOMContentLoaded', function () {
    // 範例：啟用 Bootstrap 的 Tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
