console.log("成績計算腳本已載入。");

document.addEventListener('DOMContentLoaded', function () {
    const gradeItemSelect = document.getElementById('grade-item-select');
    const tableContainer = document.getElementById('grade-entry-table-container');
    const addGradeItemBtn = document.getElementById('save-grade-item-btn');
    
    if(!gradeItemSelect) return; // 如果頁面沒有成績管理元件，就停止執行

    const addGradeItemModal = new bootstrap.Modal(document.getElementById('addGradeItemModal'));

    // --- Event Listeners ---

    // 當選擇不同的成績項目時
    gradeItemSelect.addEventListener('change', function() {
        const itemId = this.value;
        if (itemId) {
            loadGradeEntryTable(itemId);
        } else {
            tableContainer.innerHTML = '<div class="alert alert-info">請先從上方選擇一個評量項目以輸入成績。</div>';
        }
    });

    // 當點擊 "儲存" 新成績項目時
    addGradeItemBtn.addEventListener('click', async function() {
        const nameInput = document.getElementById('item-name');
        const typeInput = document.getElementById('item-type');
        const name = nameInput.value.trim();
        const type = typeInput.value;

        if (!name) {
            alert('請輸入項目名稱！');
            return;
        }

        try {
            const response = await fetch('/api/grade_items', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, type: type }),
            });
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                alert('新增成功！頁面將會重新整理。');
                window.location.reload();
            } else {
                alert('新增失敗: ' + result.message);
            }
        } catch (error) {
            console.error('Error adding grade item:', error);
            alert('新增項目時發生網路錯誤。');
        }
    });

    // --- Functions ---

    // 載入成績輸入表格
    async function loadGradeEntryTable(itemId) {
        const pathParts = window.location.pathname.split('/');
        const className = decodeURIComponent(pathParts[pathParts.length - 1]);

        try {
            tableContainer.innerHTML = '<p class="text-center text-muted">載入成績資料中...</p>';

            const gradesResponse = await fetch(`/api/grades/${itemId}?class_name=${className}`);
            if (!gradesResponse.ok) throw new Error('Failed to fetch grades.');
            const grades = await gradesResponse.json();
            
            // 使用 class_dashboard.html 模板中的學生資料來建立表格
            // 這樣可以確保順序與座位表一致
            const studentElements = document.querySelectorAll('#seating-pane .student-card-wrapper');
            let tableHTML = `
                <div class="table-responsive">
                    <table class="table table-striped table-hover table-sm">
                        <thead>
                            <tr>
                                <th class="col-4">學號</th>
                                <th class="col-4">姓名</th>
                                <th class="col-4" style="width: 120px;">分數</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            studentElements.forEach(el => {
                const studentId = el.querySelector('.student-id').textContent;
                const studentName = el.querySelector('.student-name').textContent;
                const studentDbId = el.dataset.studentId;
                const score = grades[studentDbId] !== undefined ? grades[studentDbId] : '';

                tableHTML += `
                    <tr>
                        <td>${studentId}</td>
                        <td>${studentName}</td>
                        <td>
                            <input type="number" class="form-control form-control-sm grade-input" 
                                   data-student-db-id="${studentDbId}" 
                                   data-item-id="${itemId}"
                                   value="${score}"
                                   min="0" max="100" step="0.5"
                                   placeholder="--">
                        </td>
                    </tr>
                `;
            });

            tableHTML += '</tbody></table></div>';
            tableContainer.innerHTML = tableHTML;
            
            addInputListeners();

        } catch (error) {
            console.error('Error loading grade table:', error);
            tableContainer.innerHTML = '<div class="alert alert-danger">載入成績資料失敗，請檢查網路連線或稍後再試。</div>';
        }
    }

    // 為所有成績輸入框加上事件監聽器
    function addInputListeners() {
        const inputs = document.querySelectorAll('.grade-input');
        inputs.forEach(input => {
            // 當使用者點擊其他地方時，觸發儲存
            input.addEventListener('change', (e) => saveGrade(e.target));
            
            // 【新功能】當使用者按下鍵盤時
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault(); // 阻止 Enter 的預設行為 (例如送出表單)
                    
                    // 立刻觸發儲存
                    saveGrade(e.target);

                    // 找出所有的輸入框，並計算出下一個是誰
                    const allInputs = Array.from(document.querySelectorAll('.grade-input'));
                    const currentIndex = allInputs.indexOf(e.target);
                    const nextInput = allInputs[currentIndex + 1];

                    if (nextInput) {
                        nextInput.focus(); // 將游標移到下一個輸入框
                        nextInput.select(); // 並選取裡面的文字，方便直接覆蓋
                    } else {
                        e.target.blur(); // 如果是最後一個了，就讓它失去焦點
                    }
                }
            });
        });
    }

    let saveTimeout; // 用於延遲儲存的計時器
    // 儲存單筆成績的函式
    async function saveGrade(inputElement) {
        const studentDbId = inputElement.dataset.studentDbId;
        const itemId = inputElement.dataset.itemId;
        const score = inputElement.value;

        // 提供視覺回饋：變為黃色表示處理中
        inputElement.style.backgroundColor = '#fff3cd';

        clearTimeout(saveTimeout); // 如果使用者連續輸入，清除上一次的計時
        saveTimeout = setTimeout(async () => {
            try {
                const response = await fetch('/api/grades/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ student_db_id: studentDbId, item_id: itemId, score: score }),
                });
                const result = await response.json();
                if (response.ok && result.status === 'success') {
                    // 儲存成功，變為綠色
                    inputElement.style.backgroundColor = '#d1e7dd';
                    // 短暫停留後恢復原色
                    setTimeout(() => { inputElement.style.backgroundColor = ''; }, 1200);
                } else {
                    // 儲存失敗，變為紅色
                    inputElement.style.backgroundColor = '#f8d7da';
                    alert('儲存失敗: ' + (result.message || '未知錯誤'));
                }
            } catch (error) {
                console.error('Error saving grade:', error);
                inputElement.style.backgroundColor = '#f8d7da'; // 網路錯誤，變為紅色
                alert('儲存成績時發生網路錯誤。');
            }
        }, 300); // 延遲 300 毫秒後執行，避免使用者快速輸入時造成過多請求
    }
});
