document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('seating-chart-container');
    
    // 檢查 container 是否存在，若存在才初始化 SortableJS
    if (container) {
        new Sortable(container, {
            animation: 150, // 動畫時間
            ghostClass: 'sortable-ghost', // 拖曳時的 placeholder 樣式
            // 當拖曳結束時觸發
            onEnd: function (evt) {
                const wrappers = container.querySelectorAll('.student-card-wrapper');
                let studentOrder = [];
                wrappers.forEach(wrapper => {
                    studentOrder.push(wrapper.dataset.studentId);
                });

                // 發送 API 請求到後端來儲存新的順序
                fetch('/api/update_seat_order', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ order: studentOrder }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        console.log('座位順序已成功儲存！');
                        // 可以在此處顯示一個短暫的成功訊息
                    } else {
                        console.error('儲存座位順序失敗:', data.message);
                        alert('儲存座位順序失敗，請重新整理頁面後再試一次。');
                    }
                })
                .catch((error) => {
                    console.error('Error:', error);
                    alert('與伺服器連線時發生錯誤。');
                });
            },
        });
    }
});
