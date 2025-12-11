import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import csv
import os
import re

# 数据库文件和CSV文件路径
DB_FILE = 'grades.db'
CSV_FILE = 'data.csv'

# 成绩等级与分数的映射关系
GRADE_MAPPING = {
    '优秀': 95, '优': 95,
    '良好': 85, '良': 85,
    '中等': 75, '中': 75,
    '及格': 60, '及': 60,
    '不及格': 0, '不及': 0
}

class GradeManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("学生成绩管理系统 (Linux/Python)")
        self.root.geometry("1200x700")

        # 样式设置
        style = ttk.Style()
        style.theme_use('clam')
        
        # 数据库连接
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        
        # 初始化数据
        self.columns = []
        self.db_columns = []
        self.init_database()
        
        # 构建界面
        self.create_widgets()
        self.load_data()

    def parse_score(self, value):
        """解析成绩，处理数字、文本等级和特殊格式（如 54/65）"""
        if not value:
            return 0.0
        
        value = str(value).strip()
        
        # 处理特殊格式 "54/65"，取最大值
        if '/' in value:
            parts = value.split('/')
            max_val = 0
            for part in parts:
                v = self.parse_score(part)
                if v > max_val:
                    max_val = v
            return max_val

        # 处理文本等级
        for key, score in GRADE_MAPPING.items():
            if key in value: # 包含关键词，如 "不及格/0"
                return float(score)
        
        # 处理纯数字
        try:
            return float(value)
        except ValueError:
            return 0.0

    def init_database(self):
        """初始化数据库：如果表不存在，从CSV读取表头并创建"""
        # 检查CSV是否存在以获取表头
        if not os.path.exists(CSV_FILE):
            messagebox.showerror("错误", f"未找到 {CSV_FILE} 文件！")
            return

        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
        
        # 处理表头：去除特殊字符作为数据库列名
        self.display_columns = headers
        # 将表头转换为合法的数据库列名 (去除括号、空格等)
        self.db_columns = [re.sub(r'[^\w]', '_', h).strip('_') for h in headers]
        
        # 确保有学号和姓名用于标识
        if '学号' not in self.display_columns:
            messagebox.showerror("错误", "CSV文件必须包含'学号'列")
            return

        cols_sql = ', '.join([f'"{col}" TEXT' for col in self.db_columns])
        create_table_sql = f'''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {cols_sql},
                total_score REAL DEFAULT 0,
                average_score REAL DEFAULT 0
            )
        '''
        self.cursor.execute(create_table_sql)
        self.conn.commit()

        self.cursor.execute("SELECT count(*) FROM students")
        if self.cursor.fetchone()[0] == 0:
            self.import_csv_data()

    def import_csv_data(self):
        """从CSV导入数据"""
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader) 
                
                insert_sql = f"INSERT INTO students ({', '.join(self.db_columns)}) VALUES ({', '.join(['?']*len(self.db_columns))})"
                
                for row in reader:
                    if len(row) < len(self.db_columns):
                        row += [''] * (len(self.db_columns) - len(row))
                    elif len(row) > len(self.db_columns):
                        row = row[:len(self.db_columns)]
                    self.cursor.execute(insert_sql, row)
                
                self.conn.commit()
                print("CSV数据导入成功")
        except Exception as e:
            messagebox.showerror("导入错误", str(e))

    def create_widgets(self):
        
        toolbar = ttk.Frame(self.root, padding="5")
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="添加学生", command=self.add_student).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="修改选中", command=self.edit_student).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除选中", command=self.delete_student).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(toolbar, text="计算总分/平均分", command=self.calculate_stats).pack(side=tk.LEFT, padx=2)
        
        
        ttk.Label(toolbar, text="搜索(姓名/学号):").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        entry_search = ttk.Entry(toolbar, textvariable=self.search_var)
        entry_search.pack(side=tk.LEFT, padx=2)
        entry_search.bind('<Return>', lambda e: self.load_data())
        ttk.Button(toolbar, text="查询", command=self.load_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="显示全部", command=self.reset_search).pack(side=tk.LEFT, padx=2)

        
        frame_table = ttk.Frame(self.root)
        frame_table.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        
        show_cols = self.db_columns + ['total_score', 'average_score']
        
        display_names = self.display_columns + ['总分', '平均分']

        self.tree = ttk.Treeview(frame_table, columns=show_cols, show='headings')
        
        
        v_scroll = ttk.Scrollbar(frame_table, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(frame_table, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        
        for col, name in zip(show_cols, display_names):
            self.tree.heading(col, text=name, command=lambda c=col: self.sort_treeview(c, False))
            self.tree.column(col, width=100, anchor='center')

    def load_data(self):
        """加载数据到表格"""
        
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        query = self.search_var.get().strip()
        base_sql = f"SELECT id, {', '.join(self.db_columns)}, total_score, average_score FROM students"
        
        if query:
            
            where_clause = f" WHERE 姓名 LIKE ? OR 学号 LIKE ?"
            params = (f'%{query}%', f'%{query}%')
            sql = base_sql + where_clause
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(base_sql)

        rows = self.cursor.fetchall()
        for row in rows:
            
            self.tree.insert('', 'end', iid=row[0], values=row[1:])

    def reset_search(self):
        self.search_var.set("")
        self.load_data()

    def add_student(self):
        self.open_edit_dialog(title="添加学生")

    def edit_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一名学生")
            return
        item_id = selected[0] 
        
        values = self.tree.item(item_id, 'values')
        
        raw_values = values[:len(self.db_columns)]
        self.open_edit_dialog(title="修改学生信息", data=raw_values, record_id=item_id)

    def open_edit_dialog(self, title, data=None, record_id=None):
        """通用的添加/修改弹窗"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("500x600")
        
        
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entries = {}
        for i, col_name in enumerate(self.display_columns):
            lbl = ttk.Label(scrollable_frame, text=col_name + ":")
            lbl.grid(row=i, column=0, padx=10, pady=5, sticky='e')
            
            ent = ttk.Entry(scrollable_frame, width=30)
            ent.grid(row=i, column=1, padx=10, pady=5)
            
            if data:
                ent.insert(0, data[i])
            
            entries[self.db_columns[i]] = ent

        def save():
            new_values = [entries[col].get() for col in self.db_columns]
            if record_id:
                
                set_clause = ', '.join([f"{col} = ?" for col in self.db_columns])
                sql = f"UPDATE students SET {set_clause} WHERE id = ?"
                self.cursor.execute(sql, new_values + [record_id])
            else:
                
                placeholders = ', '.join(['?'] * len(new_values))
                sql = f"INSERT INTO students ({', '.join(self.db_columns)}) VALUES ({placeholders})"
                self.cursor.execute(sql, new_values)
            
            self.conn.commit()
            self.calculate_single_student(record_id) if record_id else None 
            self.load_data()
            dialog.destroy()
            messagebox.showinfo("成功", "保存成功！")

        ttk.Button(dialog, text="保存", command=save).pack(pady=10, side=tk.BOTTOM)

    def delete_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要删除的数据")
            return
        
        if messagebox.askyesno("确认", f"确定删除选中的 {len(selected)} 条记录吗？"):
            for item_id in selected:
                self.cursor.execute("DELETE FROM students WHERE id = ?", (item_id,))
            self.conn.commit()
            self.load_data()

    def calculate_stats(self):
        """计算所有学生的总分和平均分"""
        self.cursor.execute(f"SELECT id, {', '.join(self.db_columns)} FROM students")
        rows = self.cursor.fetchall()
        
        for row in rows:
            sid = row[0]
            scores = []
            
            current_data = row[1:] 
            
            total = 0
            count = 0
            
           
            for val in current_data[2:]:
                score = self.parse_score(val)
                
                if val and str(val).strip() != '':
                    total += score
                    count += 1
            
            avg = total / count if count > 0 else 0
            
            self.cursor.execute("UPDATE students SET total_score = ?, average_score = ? WHERE id = ?", (total, round(avg, 2), sid))
        
        self.conn.commit()
        self.load_data()
        messagebox.showinfo("完成", "所有学生成绩统计完成！")
    
    def calculate_single_student(self, sid):
        
        pass

    def sort_treeview(self, col, reverse):
        """按列排序"""
        
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        try:
            l.sort(key=lambda t: float(t[0]) if t[0] else -1, reverse=reverse)
        except ValueError:
            l.sort(key=lambda t: t[0], reverse=reverse)

        
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

if __name__ == "__main__":
    root = tk.Tk()
    app = GradeManagementSystem(root)
    root.mainloop()