document.addEventListener('DOMContentLoaded', function () {
    const grid = document.getElementById('seating-chart-grid');
    const layoutRadios = document.querySelectorAll('input[name="layout-switch"]');
    const saveBtn = document.getElementById('save-seating-chart-btn');

    // 如果頁面上沒有座位表元件，就停止執行
    if (!grid) {
        return;
    }

    // --- 事件監聽器 ---

    if (saveBtn) {
        saveBtn.addEventListener('click', saveSeatingChart);
    }
    
    // 為佈局切換按鈕加上事件監聽器
    layoutRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                const confirmation = confirm('切換座位表佈局將會清除所有已排定的座位，您確定要繼續嗎？');
                if (confirmation) {
                    updateLayout(this.dataset.layout);
                } else {
                    // 如果使用者取消，把按鈕切換回來
                    window.location.reload();
                }
            }
        });
    });

    // --- SortableJS 初始化 ---
    
    // 為每一個座位格啟用 Sortable，以達成交換效果
    const seatSlots = document.querySelectorAll('.seat-slot');
    seatSlots.forEach(slot => {
        new Sortable(slot, {
            group: 'students', // 必須設為相同群組才能互相拖曳
            animation: 150,
            ghostClass: 'sortable-ghost',
            // 當有學生卡片被放入此座位格時觸發
            onAdd: function (evt) {
                const fromSlot = evt.from; // 來源座位格
                const toSlot = evt.to;     // 目標座位格 (也就是目前的 slot)
                const draggedItem = evt.item; // 被拖曳的學生卡片

                // 如果目標座位格在加入後有超過一個學生（代表裡面原本有人）
                // 就把原本在裡面的學生移回來源座位格
                if (fromSlot.children.length === 0 && toSlot.children.length > 1) {
                    for (const child of toSlot.children) {
                        if (child !== draggedItem) {
                            fromSlot.appendChild(child);
                            break; // 應該只會有一個，找到就跳出
                        }
                    }
                }
            }
        });
    });

    // --- 函式 ---
    
    /**
     * 收集目前的座位表佈局並透過 API 儲存
     */
    async function saveSeatingChart() {
        const assignments = [];
        const slots = document.querySelectorAll('#seating-chart-grid .seat-slot');
        
        slots.forEach(slot => {
            const studentCard = slot.querySelector('.student-card-wrapper');
            if (studentCard) {
                assignments.push({
                    student_id: studentCard.dataset.studentId,
                    row: slot.dataset.row,
                    col: slot.dataset.col
                });
            }
        });

        saveBtn.disabled = true;
        saveBtn.textContent = '儲存中...';

        try {
            const response = await fetch('/api/save_seating_chart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ assignments: assignments }),
            });
            const data = await response.json();
            if (data.status === 'success') {
                alert('座位表已成功儲存！');
            } else {
                throw new Error('儲存失敗: ' + (data.message || ''));
            }
        } catch (error) {
            console.error('儲存座位表時發生錯誤:', error);
            alert('儲存座位表時發生錯誤。');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = '儲存座位表';
        }
    }
    
    /**
     * 透過 API 更新班級的座位表佈局
     * @param {string} newLayout - 新的佈局字串，例如 '6x6'
     */
    async function updateLayout(newLayout) {
        const pathParts = window.location.pathname.split('/');
        const className = decodeURIComponent(pathParts[pathParts.length - 1]);
        try {
             const response = await fetch('/api/update_layout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ class_name: className, layout: newLayout }),
            });
            const data = await response.json();
            if (data.status === 'success') {
                window.location.reload(); 
            } else {
                 throw new Error('更新佈局失敗');
            }
        } catch (error) {
            console.error('更新佈局時發生錯誤:', error);
            alert('更新佈局時發生錯誤。');
        }
    }
});

