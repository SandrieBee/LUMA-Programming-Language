import customtkinter as ctk
import tkinter as tk
import subprocess
import os
import threading
import re

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class LumaIDE(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Luma IDE (Strict Parser Edition)")
        self.geometry("1200x800")
        
        # --- State Management ---
        self.current_file_path = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # --- COMPILER PATH SETTING ---
        # UPDATED: Hardcoded path to your specific executable location 
        self.compiler_path = r"D:\Documents\112\Luma Programming Language\v2\luma.exe"  

        # --- GRID LAYOUT ---
        self.grid_rowconfigure(0, weight=0)  # Toolbar
        self.grid_rowconfigure(1, weight=3)  # Editor
        self.grid_rowconfigure(2, weight=1)  # Bottom Panels
        self.grid_columnconfigure(0, weight=3) # Editor/Bottom
        self.grid_columnconfigure(1, weight=1) # Output

        self._create_ui()

    def _create_ui(self):
        # 1. TOOLBAR
        self.toolbar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=(10, 5))

        ctk.CTkLabel(self.toolbar, text="LUMA IDE", font=("Arial", 16, "bold")).pack(side="left", padx=15)
        
        ctk.CTkButton(self.toolbar, text="📂 Open", width=80, command=self.open_file).pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="📄 New", width=80, command=self.new_file).pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="ℹ️ Instruction", width=100, command=self.show_instructions).pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="💾 Save", width=80, command=self.save_file).pack(side="left", padx=5)
        
        self.btn_run = ctk.CTkButton(self.toolbar, text="▶ RUN PARSER", width=120, fg_color="green", hover_color="darkgreen", command=self.run_code_thread)
        self.btn_run.pack(side="right", padx=20)

        # 2. EDITOR AREA (Left)
        self.editor_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.editor_frame.grid(row=1, column=0, sticky="nsew", padx=3, pady=3)
        
        # --- EDITOR FONTS & COLORS ---
        editor_font = ("Consolas", 14)
        bg_color = "#2b2b2b"
        fg_color = "#d4d4d4"
        linenum_bg = "#1e1e1e"
        linenum_fg = "gray"

        # A. Line Numbers
        self.line_numbers = tk.Text(self.editor_frame, width=4, font=editor_font, 
                                    bg=linenum_bg, fg=linenum_fg, 
                                    bd=0, highlightthickness=0, state="disabled")
        self.line_numbers.pack(side="left", fill="y")
        
        # B. Scrollbar
        self.scrollbar = ctk.CTkScrollbar(self.editor_frame, command=self._on_scrollbar_move)
        self.scrollbar.pack(side="right", fill="y")

        # C. Main Editor
        self.editor = tk.Text(self.editor_frame, font=editor_font, 
                              bg=bg_color, fg=fg_color,
                              bd=0, highlightthickness=0,
                              undo=True, insertbackground="white") 
        self.editor.pack(side="left", fill="both", expand=True)

        # --- SETUP DEFAULT CODE ---
        default_code = (
            '$ Luma Code\n'
            'let x = 10\n'
            'let y = 20\n'
            'display "The value is: " + x\n'
        )
        self.editor.insert("1.0", default_code)
        
        # --- BINDING EVENTS ---
        self.editor.bind("<KeyRelease>", self._on_content_changed)
        self.editor.bind("<MouseWheel>", self._on_mousewheel) 
        self.editor.bind("<Button-4>", self._on_mousewheel)   
        self.editor.bind("<Button-5>", self._on_mousewheel)   
        self.editor.config(yscrollcommand=self._on_text_scroll)
        
        self._update_line_numbers()

        # 3. OUTPUT (Right)
        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.output_frame, text="PARSER OUTPUT", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)
        self.console = ctk.CTkTextbox(self.output_frame, font=("Consolas", 12), state="disabled", fg_color="#1e1e1e", text_color="#00ff00")
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

        # 4. BOTTOM PANELS (Left)
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(1, weight=1)
        self.bottom_frame.grid_rowconfigure(0, weight=1)

        # Assembly Panel
        self.asm_panel = ctk.CTkFrame(self.bottom_frame)
        self.asm_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(self.asm_panel, text="ASSEMBLY GENERATION", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)
        self.asm_box = ctk.CTkTextbox(self.asm_panel, font=("Consolas", 12), text_color="#9cdcfe")
        self.asm_box.pack(fill="both", expand=True, padx=5, pady=5)

        # Machine Code Panel
        self.mach_panel = ctk.CTkFrame(self.bottom_frame)
        self.mach_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        mach_header = ctk.CTkFrame(self.mach_panel, fg_color="transparent", height=20)
        mach_header.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(mach_header, text="MACHINE CODE", font=("Arial", 12, "bold")).pack(side="left")
        ctk.CTkLabel(mach_header, text="HEX | BINARY", font=("Arial", 10), text_color="gray").pack(side="right")

        self.mach_box = ctk.CTkTextbox(self.mach_panel, font=("Consolas", 12), text_color="#ce9178")
        self.mach_box.pack(fill="both", expand=True, padx=5, pady=5)

    # --- SCROLL & LINE NUMBER SYNC ---
    def _on_scrollbar_move(self, *args):
        self.editor.yview(*args)
        self.line_numbers.yview(*args)

    def _on_text_scroll(self, *args):
        self.scrollbar.set(*args)
        self._sync_yview()

    def _on_mousewheel(self, event):
        self.after(1, self._sync_yview)

    def _sync_yview(self):
        try:
            pos = self.editor.yview()
            self.line_numbers.yview_moveto(pos[0])
        except: pass

    def _on_content_changed(self, event=None):
        self._update_line_numbers()

    def _update_line_numbers(self):
        code = self.editor.get("1.0", "end-1c")
        lines = code.count("\n") + 1
        line_string = "\n".join(str(i) for i in range(1, lines + 1))
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end") 
        self.line_numbers.insert("1.0", line_string)
        self.line_numbers.configure(state="disabled")
        self._sync_yview()

    # --- EXECUTION ENGINE ---
    def run_code_thread(self):
        code = self.editor.get("1.0", "end-1c")
        self.console.configure(state="normal")
        self.console.delete("0.0", "end")
        self.console.configure(state="disabled")
        threading.Thread(target=self._execution_logic, args=(code,)).start()

    def _execution_logic(self, code):
        # 1. Generate Assembly (Visual only, distinct from Parser execution)
        self._generate_edumips64_translation(code)

        # 2. STRICTLY Run External Compiler
        # Check if the hardcoded path exists
        if not os.path.exists(self.compiler_path):
            self.after(0, lambda: self.log_output(f"CRITICAL ERROR: Parser not found!", "error"))
            self.after(0, lambda: self.log_output(f"Looking at: {self.compiler_path}", "error"))
            self.after(0, lambda: self.log_output(f"Please check the path in Python code (Line 26).", "error"))
            return

        self.after(0, lambda: self.log_output(f"--- Running Parser ---", "gray"))
        
        # Execute the C program
        output, error = self._run_external_compiler(code)
        
        # Display Results from C Program
        if error:
            self.after(0, lambda: self.log_output(error, "error"))
            self.after(0, lambda: self.log_output("\n[Execution Failed]", "error"))
        elif output:
            self.after(0, lambda: self.log_output(output))
            self.after(0, lambda: self.log_output("\n[Execution Successful]", "gray"))
        else:
            self.after(0, lambda: self.log_output("[Program ran but produced no output]", "gray"))

    def _run_external_compiler(self, code):
        """Runs the compiled C program and pipes its output."""
        # Note: We create a temp file because your parser reads from stdin or file.
        temp_file = os.path.join(self.script_dir, "temp.lm")
        try:
            # Ensure code has a newline at the end to prevent EOF errors in Parser
            if not code.endswith("\n"):
                code += "\n"

            with open(temp_file, "w") as f: 
                f.write(code)
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Execute the compiled parser
            # We redirect stdin to the file we just wrote
            result = subprocess.run(
                [self.compiler_path], 
                input=code, 
                capture_output=True, 
                text=True, 
                startupinfo=startupinfo, 
                timeout=5
            )
            
            # If returncode is not 0 (e.g., return 1 from main), we treat stderr as the primary info
            if result.returncode != 0:
                return result.stdout, result.stderr # Return both, as parser might print partial output then error
            else:
                return result.stdout, None
                
        except Exception as e:
            return None, str(e)
        finally:
            if os.path.exists(temp_file): os.remove(temp_file)

    # --- EDUMIPS64 GENERATOR (VISUAL ONLY) ---
    def _calculate_rtype_hex(self, opcode, rs, rt, rd, shamt, funct):
        val = (opcode << 26) | (rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct
        return f"{val:08X}"

    def _generate_edumips64_translation(self, code):
        # This function generates the Assembly view, but does NOT execute logic.
        asm_lines = [".data"]
        text_lines = [".code"]
        mach_lines = []
        
        reg_count = 1 
        str_count = 0
        var_mem_offset = 8
        var_map = {} 

        lines = code.split('\n')
        
        # Pre-scan for strings
        for line in lines:
            if "display" in line and '"' in line:
                str_match = re.search(r'"(.*?)"', line)
                if str_match:
                    asm_lines.append(f"  str{str_count}: .asciiz \"{str_match.group(1)}\"")
                    str_count += 1

        str_current = 0

        for line in lines:
            line = line.split('$')[0].strip()
            if not line: continue
            
            # 1. Char Declaration
            char_match = re.match(r"let\s+(\w+)\s*=\s*'([^'])'", line)
            if char_match:
                var, char_val = char_match.groups()
                val = ord(char_val)
                asm_lines.append(f"  {var}: .byte {val}")
                text_lines.append(f"  LD R{reg_count}, {var}(R0)")
                mach_lines.append(f"DC0{reg_count}{var_mem_offset:04X}")
                var_map[var] = reg_count
                var_mem_offset += 8
                reg_count += 1
                continue

           # 2. Variable Assignment
            assign_match = re.match(r"let\s+(\w+)\s*=\s*([a-zA-Z_]\w*)$", line)
            if assign_match:
                target, source = assign_match.groups()
                if source in var_map:
                    src_reg = var_map[source]
                    asm_lines.append(f"  {target}: .word64 0") 
                    text_lines.append(f"  DADD R{reg_count}, R{src_reg}, R0")
                    mach_lines.append(self._calculate_rtype_hex(0, src_reg, 0, reg_count, 0, 0x2C))
                    text_lines.append(f"  SD R{reg_count}, {target}(R0)")
                    sd_val = (63 << 26) | (0 << 21) | (reg_count << 16) | (var_mem_offset & 0xFFFF)
                    mach_lines.append(f"{sd_val:08X}")
                    var_map[target] = reg_count
                    var_mem_offset += 8
                    reg_count += 1
                continue

            # 3. Integer Declaration
            let_match = re.match(r'let\s+(\w+)\s*=\s*(\d+)', line)
            if let_match:
                var, val = let_match.groups()
                asm_lines.append(f"  {var}: .word64 {val}")
                text_lines.append(f"  LD R{reg_count}, {var}(R0)")
                mach_lines.append(f"DC0{reg_count}{var_mem_offset:04X}") 
                var_map[var] = reg_count
                var_mem_offset += 8
                reg_count += 1
                continue

            # 4. Math
            math_match = re.match(r"let\s+(\w+)\s*=\s*(\w+)\s*\+\s*(\w+)", line)
            if math_match:
                target, op1, op2 = math_match.groups()
                rs = var_map.get(op1, reg_count-1)
                rt = var_map.get(op2, reg_count-2)
                asm_lines.append(f"  {target}: .word64 0")
                text_lines.append(f"  DADD R{reg_count}, R{rs}, R{rt}")
                mach_lines.append(self._calculate_rtype_hex(0, rs, rt, reg_count, 0, 0x2C))
                text_lines.append(f"  SD R{reg_count}, {target}(R0)")
                sd_val = (63 << 26) | (0 << 21) | (reg_count << 16) | (var_mem_offset & 0xFFFF)
                mach_lines.append(f"{sd_val:08X}")
                var_map[target] = reg_count
                var_mem_offset += 8
                reg_count += 1
                continue

            # 5. Display
            if "display" in line:
                if '"' in line:
                    text_lines.append(f"  DADDU R4, R0, str{str_current}")
                    mach_lines.append(f"600400{str_current}0")
                    mach_lines.append("600E0004")
                    mach_lines.append("0000000C")
                    str_current += 1
                else:
                    disp_match = re.match(r"display\s+([a-zA-Z_]\w*)", line)
                    if disp_match:
                        var_name = disp_match.group(1)
                        target_reg = var_map.get(var_name, reg_count - 1)
                        text_lines.append(f"  DADDU R1, R0, R{target_reg}") 
                        mach_lines.append(self._calculate_rtype_hex(0, 0, target_reg, 1, 0, 0x2C))
                        mach_lines.append("600E0001")
                        mach_lines.append("0000000C")

        text_lines.append("  SYSCALL 0")
        full_asm = "\n".join(asm_lines) + "\n\n" + "\n".join(text_lines)
        
        full_mach = ""
        for h in mach_lines:
            try:
                i = int(h, 16)
                binary = f"{i:032b}"
                full_mach += f"{h}  |  {binary}\n"
            except: pass

        self.after(0, lambda: self._update_box(self.asm_box, full_asm))
        self.after(0, lambda: self._update_box(self.mach_box, full_mach))

    def _update_box(self, box, text):
        box.configure(state="normal")
        box.delete("0.0", "end")
        box.insert("0.0", text)
        box.configure(state="disabled")

    def log_output(self, message, msg_type="info"):
        self.console.configure(state="normal")
        prefix = ""
        tag = "normal"
        
        if msg_type == "error": 
            prefix = "" 
            tag = "error"
            self.console.tag_config("error", foreground="red")
        elif msg_type == "gray": 
            prefix = ""
            tag = "gray"
            self.console.tag_config("gray", foreground="gray")
            
        self.console.insert("end", f"{prefix}{message}\n", tag)
        self.console.configure(state="disabled")
        self.console.see("end")

    # --- FILE OPS ---
    def new_file(self):
        self.editor.delete("1.0", "end")
        self.current_file_path = None
        self._update_line_numbers()
        self.log_output("New file", "gray")

    def open_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Luma", "*.lm"), ("Txt", "*.*")])
        if path:
            with open(path, "r") as f:
                self.editor.delete("1.0", "end")
                self.editor.insert("1.0", f.read())
            self.current_file_path = path
            self._update_line_numbers()
            self.log_output(f"Loaded {os.path.basename(path)}", "gray")

    def save_file(self):
        if self.current_file_path:
            with open(self.current_file_path, "w") as f:
                f.write(self.editor.get("1.0", "end-1c"))
            self.log_output("Saved", "gray")
        else:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".lm")
            if path:
                self.current_file_path = path
                self.save_file()

    def show_instructions(self):
        from tkinter import messagebox
        messagebox.showinfo("Help", "Luma Syntax:\n\nlet a = 10\nlet sum = a + b\ndisplay sum")

if __name__ == "__main__":
    app = LumaIDE()
    app.mainloop()