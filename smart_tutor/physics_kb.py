"""
Smart Tutor · 内置大学物理知识库
===============================
涵盖力学、电磁学、热学、光学、量子物理、原子物理、
半导体物理等核心大物知识点。

每个知识点包含：
- 基础层级描述
- 进阶层级（公式 + 深层原理）
- 关联知识点（知识图谱边）
- 现实应用（日常→工程→科研）
- 考题概率 ★~★★★★★
- 常见题型
"""

import json
import re
import random
from typing import Optional

# ══════════════════════════════════════════════════════════════════
# 核心知识库
# ══════════════════════════════════════════════════════════════════

PHYSICS_KNOWLEDGE = {
    # ── 力学 ──────────────────────────────────────────────────
    "牛顿运动定律": {
        "subject": "力学",
        "basic": "牛顿三定律是经典力学的基础。第一定律（惯性定律）：物体保持静止或匀速直线运动，除非外力作用。第二定律：F=ma，力等于质量乘以加速度。第三定律：作用力与反作用力大小相等方向相反。",
        "advanced": "在非惯性系中需引入惯性力。F=ma 在相对论下修正为 F=dp/dt，其中 p=γmv。分析力学中用拉格朗日方程 L=T-V 推导运动方程。",
        "formulas": ["F = ma", "F₁₂ = -F₂₁", "F = dp/dt", "F_f = μN"],
        "related": ["受力分析", "功与能", "动量守恒", "圆周运动", "简谐振动"],
        "applications": {
            "daily": "汽车安全带利用惯性原理，刹车时防止前冲；电梯超重失重感觉",
            "engineering": "火箭推进：F=ma 结合动量守恒计算推力；车辆碰撞测试中的力分析",
            "research": "微重力实验中的惯性导航；微纳尺度下摩擦力与经典定律的偏差研究"
        },
        "exam_probability": 5,
        "common_types": ["计算题", "证明题", "概念辨析"],
        "contrast": None
    },
    "受力分析": {
        "subject": "力学",
        "basic": "受力分析是解决力学问题的第一步。步骤：①确定研究对象 ②画出所有外力（重力、弹力、摩擦力、拉力等）③建立坐标系 ④正交分解 ⑤列方程求解。",
        "advanced": "约束力分析：光滑面约束（法向）、铰链约束（方向未知）、柔索约束（沿绳方向）。虚功原理可避免求约束力直接求解平衡条件。",
        "formulas": ["ΣF_x = 0", "ΣF_y = 0", "Στ = 0", "f = μN（滑动摩擦力）"],
        "related": ["牛顿运动定律", "力矩与转动平衡", "静力学"],
        "applications": {
            "daily": "搬重物时斜拉比直拉省力（力的分解）；斜面上的物体滑不滑取决于角度和摩擦系数",
            "engineering": "桥梁桁架结构的节点受力分析；建筑抗震设计中的地震力分析",
            "research": "仿生机器人关节受力分析；细胞骨架的力学平衡"
        },
        "exam_probability": 5,
        "common_types": ["计算题", "作图题"],
        "contrast": {
            "概念A": "内力和外力",
            "A说明": "外力是系统外物体对系统内物体的力；内力是系统内物体间的相互作用",
            "概念B": "作用力和反作用力",
            "B说明": "作用力和反作用力分别作用在两个不同物体上",
            "区别": "一对平衡力作用在同一物体上；一对作用力反作用力作用在不同物体上"
        }
    },
    "动量守恒": {
        "subject": "力学",
        "basic": "系统所受合外力为零时，系统的总动量保持不变。m₁v₁ + m₂v₂ = m₁v₁' + m₂v₂'。适用于碰撞、爆炸、反冲等过程。",
        "advanced": "变质量体系（火箭方程）：m dv/dt = F_ext + v_rel dm/dt。在量子力学中，动量守恒对应于空间平移对称性（诺特定理）。相对论动量 p = γmv。",
        "formulas": ["p = mv", "Δp = FΔt（冲量定理）", "m₁v₁+m₂v₂ = m₁v₁'+m₂v₂'", "F_ext = dp/dt"],
        "related": ["牛顿运动定律", "能量守恒", "碰撞问题", "火箭推进"],
        "applications": {
            "daily": "开枪时后坐力（枪和子弹动量守恒）；冰面上两个人互相推离",
            "engineering": "火箭推进：喷出高速燃气的动量等于火箭获得的动量；汽车安全气囊通过延长碰撞时间减小冲击力",
            "research": "粒子对撞机中利用动量守恒重建碰撞前的粒子状态；离子推进器的动量传递"
        },
        "exam_probability": 5,
        "common_types": ["计算题", "综合题"],
        "contrast": {
            "概念A": "动量守恒",
            "A说明": "合外力为零时系统总动量守恒",
            "概念B": "机械能守恒",
            "B说明": "只有保守力做功时机械能守恒",
            "区别": "动量守恒是矢量守恒，能量守恒是标量守恒。非弹性碰撞动量守恒但机械能不守恒"
        }
    },
    "功与能": {
        "subject": "力学",
        "basic": "功 W = F·s·cosθ，是力在位移上的积累。动能 E_k = ½mv²，势能包括重力势能 mgh、弹性势能 ½kx²。功能原理：合外力做功等于动能的变化。",
        "advanced": "保守力做功与路径无关，可引入势能。机械能守恒：只有保守力做功时 E_k+E_p=常数。变力做功需积分 W=∫F·dl。广义坐标下的拉格朗日力学。",
        "formulas": ["W = F·s·cosθ", "E_k = ½mv²", "E_p = mgh", "E_p = ½kx²", "W = ΔE_k"],
        "related": ["牛顿运动定律", "动量守恒", "简谐振动"],
        "applications": {
            "daily": "骑车上坡时势能增加→动能减小→需要更用力蹬",
            "engineering": "水力发电：水的重力势能→动能→电能；飞轮储能技术",
            "research": "纳米尺度下能量量子化；能量收集（energy harvesting）技术"
        },
        "exam_probability": 5,
        "common_types": ["计算题", "综合题"],
        "contrast": None
    },
    "圆周运动与万有引力": {
        "subject": "力学",
        "basic": "匀速圆周运动：向心加速度 a = v²/r = ω²r，向心力 F = mv²/r。万有引力定律 F = Gm₁m₂/r²，行星运动遵循开普勒三定律。",
        "advanced": "非匀速圆周运动有切向加速度 a_t = dv/dt。开普勒定律可由万有引力+牛顿定律推导。引力势能 E_p = -GMm/r。轨道力学中角动量守恒导致面积速度恒定。",
        "formulas": ["a_c = v²/r", "F_c = mv²/r", "F_g = Gm₁m₂/r²", "T² = (4π²/GM)r³"],
        "related": ["牛顿运动定律", "功与能", "角动量守恒"],
        "applications": {
            "daily": "游乐场过山车在最高点不掉下来（向心力来自重力和轨道支持力）",
            "engineering": "卫星轨道设计；GPS定位需修正广义相对论引力时间膨胀效应",
            "research": "引力波探测（LIGO）；黑洞附近强引力场中的轨道进动"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "推导题"],
        "contrast": None
    },
    "简谐振动": {
        "subject": "力学",
        "basic": "回复力与位移成正比且反向 F = -kx 的运动。运动方程 x = Acos(ωt+φ)，角频率 ω = √(k/m)，周期 T = 2π√(m/k)。能量：E = ½kA²。",
        "advanced": "阻尼振动：振幅随时间指数衰减 x = Ae^(-βt)cos(ωt+φ)。受迫振动共振条件 ω_drive = ω_0。李萨如图形。耦合振子简正模分析。",
        "formulas": ["F = -kx", "x = Acos(ωt+φ)", "ω = √(k/m)", "T = 2π√(m/k)", "E = ½kA²"],
        "related": ["功与能", "波动", "电磁振荡"],
        "applications": {
            "daily": "钟摆的等时性；吉他弦振动频率与张力的关系",
            "engineering": "减震器设计（阻尼振动）；建筑抗震：调谐质量阻尼器",
            "research": "原子力显微镜（AFM）悬臂梁的共振模式；量子谐振子与零点能"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "图像分析", "综合题"],
        "contrast": None
    },
    "波动": {
        "subject": "力学/波动光学",
        "basic": "机械波是振动在介质中的传播。波速 v = λf = ω/k。平面波表达式 y = Acos(ωt - kx)。波的干涉：同频率同方向两列波叠加产生加强或减弱。",
        "advanced": "驻波由两列反向传播的同频波叠加而成，波节波腹间隔 λ/2。多普勒效应：f' = f(v±v₀)/(v∓v_s)。惠更斯原理。群速度与相速度。",
        "formulas": ["v = λf", "y = Acos(ωt - kx)", "Δφ = 2πΔr/λ", "v = √(T/μ)（弦波速）"],
        "related": ["简谐振动", "光的干涉衍射", "声学"],
        "applications": {
            "daily": "回声定位（蝙蝠超声波）；乐器共鸣箱放大声音",
            "engineering": "超声无损检测；地震波勘探；手机天线电磁波传播",
            "research": "引力波探测：LIGO利用激光干涉测量10⁻¹⁸m的位移；声子晶体"
        },
        "exam_probability": 3,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    # ── 电磁学 ────────────────────────────────────────────────
    "库仑定律与电场": {
        "subject": "电磁学",
        "basic": "库仑定律：F = kq₁q₂/r²，同号相斥异号相吸。电场强度 E = F/q₀ = kQ/r²。电场叠加原理：多个点电荷的电场为矢量叠加。",
        "advanced": "连续电荷分布的电场：E = ∫kdq/r²。电偶极子在均匀电场中受转矩 τ = p×E。电场能量密度 u = ½ε₀E²。",
        "formulas": ["F = kq₁q₂/r²", "E = kQ/r²", "E = -∇V", "U = qV"],
        "related": ["高斯定理", "电势与电势差", "静电场中的导体"],
        "applications": {
            "daily": "静电复印（静电吸附碳粉）；梳头后梳子吸引小纸片",
            "engineering": "静电除尘器（工业废气处理）；电容式触摸屏原理",
            "research": "扫描隧道显微镜（STM）：利用尖端与样品间的电场隧穿效应"
        },
        "exam_probability": 5,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    "高斯定理": {
        "subject": "电磁学",
        "basic": "高斯定理：通过闭合曲面的电通量等于内部电荷除以 ε₀。∮E·dA = Q_enc/ε₀。对于高度对称的电荷分布（球对称、柱对称、平面对称），可用高斯定理简洁地求电场。",
        "advanced": "微分形式：∇·E = ρ/ε₀。介质中的高斯定理：∮D·dA = Q_free，其中 D = ε₀E + P = εE。高斯定理是麦克斯韦方程组之一。",
        "formulas": ["∮E·dA = Q/ε₀", "∇·E = ρ/ε₀", "∮D·dA = Q_free", "D = εE"],
        "related": ["库仑定律与电场", "电势与电势差", "静电场中的导体"],
        "applications": {
            "daily": "微波炉门上的金属网（法拉第笼）利用静电屏蔽原理",
            "engineering": "同轴电缆的电场分析和屏蔽设计；高压设备外壳的静电屏蔽",
            "research": "凝聚态物理中的屏蔽效应（Thomas-Fermi屏蔽长度）"
        },
        "exam_probability": 5,
        "common_types": ["计算题", "证明题"],
        "contrast": {
            "概念A": "电场强度 E",
            "A说明": "描述电场力的属性，∮E·dA = Q/ε₀",
            "概念B": "电位移 D",
            "B说明": "描述自由电荷产生的场，∮D·dA = Q_free",
            "区别": "E依赖介质分布，D仅依赖自由电荷分布。D=εE在均匀各向同性介质中成立"
        }
    },
    "电势与电势差": {
        "subject": "电磁学",
        "basic": "电势差 V_ab = W_ab/q₀ = -∫E·dl。点电荷电势 V = kQ/r。等势面垂直于电场线。电场强度与电势的关系：E = -∇V（负梯度方向）。",
        "advanced": "电势多极展开：V = k(Q/r + p·r̂/r² + Q_ijx_i x_j/2r³ + ...)。拉普拉斯方程 ∇²V = 0。镜像法求解边界值问题。",
        "formulas": ["V_ab = -∫E·dl", "V = kQ/r（点电荷）", "E = -dV/dx（一维）", "U = qV（电势能）"],
        "related": ["库仑定律与电场", "高斯定理", "电容与电容器"],
        "applications": {
            "daily": "高压输电线的电势梯度；静电感应（靠近带电体时验电器箔片张开）",
            "engineering": "心脏起搏器的电势检测；接地保护（使外壳电势为零）",
            "research": "半导体 PN 结内建电势；电化学电池的电极电势"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    "电容与电容器": {
        "subject": "电磁学",
        "basic": "电容 C = Q/V，单位法拉（F）。平行板电容器 C = ε₀S/d。串联：1/C_eq = Σ1/C_i，并联：C_eq = ΣC_i。电容器储能 W = ½CV²。",
        "advanced": "介质电容：C = ε_rC₀。插入介质时若保持电荷不变则电场减弱。静电势能密度 u = ½ε₀E²。实际电容器有耐压限制和漏电流。",
        "formulas": ["C = Q/V", "C = ε₀S/d", "W = ½CV² = Q²/2C", "u = ½εE²"],
        "related": ["电势与电势差", "静电场中的导体", "RC电路"],
        "applications": {
            "daily": "手机触摸屏（电容式感应）；相机闪光灯电容快速放电",
            "engineering": "超级电容器储能（电动汽车）；滤波电容平滑整流输出",
            "research": "纳米电容器（MEMS）；量子电容（二维电子气）"
        },
        "exam_probability": 3,
        "common_types": ["计算题", "电路分析"],
        "contrast": None
    },
    "静电场中的导体": {
        "subject": "电磁学",
        "basic": "静电平衡时：内部电场为零，表面电场垂直于表面，整个导体等势。电荷分布在表面。尖端放电：曲率越大电荷密度越大。静电屏蔽。",
        "advanced": "唯一性定理保证给定边界条件电势唯一。电像法：点电荷在导体平面前等效为镜像电荷。导体腔：外场不影响腔内（法拉第笼）。",
        "formulas": ["E_inside = 0", "V = const", "σ ∝ 1/R（曲率半径）", "E_surface = σ/ε₀"],
        "related": ["高斯定理", "电势与电势差", "电容与电容器"],
        "applications": {
            "daily": "避雷针（尖端放电引雷入地）；电梯厢是法拉第笼，雷电时车内安全",
            "engineering": "精密电子设备电磁屏蔽；高压输电线的电晕放电抑制",
            "research": "扫描电子显微镜（SEM）中的电子束聚焦与偏转"
        },
        "exam_probability": 3,
        "common_types": ["概念题", "证明题"],
        "contrast": None
    },
    "恒磁场与毕奥-萨伐尔定律": {
        "subject": "电磁学",
        "basic": "电流产生磁场。毕奥-萨伐尔定律：dB = (μ₀/4π)(Idl×r̂)/r²。长直导线 B = μ₀I/2πr。圆形电流圆心处 B = μ₀I/2R。",
        "advanced": "运动电荷的磁场 B = (μ₀/4π)qv×r̂/r²。矢量磁位 A：B = ∇×A，∇²A = -μ₀J。磁偶极矩 m = IS，在均匀磁场中受转矩 τ = m×B。",
        "formulas": ["dB = (μ₀/4π)Idl×r̂/r²", "B = μ₀I/2πr（长直）", "B = μ₀I/2R（圆心）", "F = qv×B（洛伦兹力）"],
        "related": ["安培环路定理", "电磁感应", "洛伦兹力"],
        "applications": {
            "daily": "指南针（地磁场对磁针的力矩）；电磁炉（涡流加热）",
            "engineering": "磁悬浮列车；粒子加速器中的二极磁铁偏转粒子束",
            "research": "核磁共振（NMR）中的强磁场（超导磁体）；LHC 的∼8T超导磁铁"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "综合题"],
        "contrast": None
    },
    "安培环路定理": {
        "subject": "电磁学",
        "basic": "安培环路定理：∮B·dl = μ₀I_enc。磁场沿闭合回路的环量等于穿过回路的总电流乘以 μ₀。适用于对称电流分布求磁场。",
        "advanced": "位移电流修正（麦克斯韦）：∮B·dl = μ₀(I_enc + ε₀dΦ_E/dt)。微分形式：∇×B = μ₀J + μ₀ε₀∂E/∂t。介质中的 H 场：∮H·dl = I_free。",
        "formulas": ["∮B·dl = μ₀I_enc", "∇×B = μ₀J", "∮H·dl = I_free", "B = μ₀μ_rH"],
        "related": ["恒磁场与毕奥-萨伐尔定律", "电磁感应", "麦克斯韦方程组"],
        "applications": {
            "daily": "电磁炉的涡流加热（变化的磁场在锅底感应涡流）",
            "engineering": "变压器铁芯中的磁路分析；电磁铁设计",
            "research": "托卡马克聚变装置中的等离子体磁约束"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "证明题"],
        "contrast": {
            "概念A": "安培环路定理",
            "A说明": "∮B·dl = μ₀I_enc，环量等于穿过的电流",
            "概念B": "高斯定理（磁场）",
            "B说明": "∮B·dA = 0，磁通量进出闭合面为零",
            "区别": "安培环路对应磁场的旋度（有源），高斯磁定理对应散度（无源）。磁场无磁单极"
        }
    },
    "电磁感应": {
        "subject": "电磁学",
        "basic": "法拉第电磁感应定律：ε = -dΦ_B/dt。闭合回路中的感应电动势等于磁通量变化率的负值。楞次定律：感应电流的方向总是阻碍引起它的磁通变化。",
        "advanced": "动生电动势：ε = ∮(v×B)·dl（导体切割磁感线）。感生电场：∇×E = -∂B/∂t。自感 ε_L = -L dI/dt，互感 ε₂ = -M dI₁/dt。",
        "formulas": ["ε = -dΦ/dt", "ε = Blv（切割磁感线）", "ε_L = -L dI/dt", "U_m = ½LI²（磁场储能）"],
        "related": ["恒磁场", "安培环路定理", "麦克斯韦方程组", "交流电路"],
        "applications": {
            "daily": "手机无线充电（电磁感应原理）；电磁炉加热",
            "engineering": "发电机（机械能→电能）；变压器（电压变换）；涡流制动（高铁刹车）",
            "research": "磁悬浮列车中的电磁感应悬浮系统；感应式粒子加速器"
        },
        "exam_probability": 5,
        "common_types": ["计算题", "综合题"],
        "contrast": None
    },
    "麦克斯韦方程组": {
        "subject": "电磁学",
        "basic": "麦克斯韦方程组是电磁学的基石，包含四个方程：①高斯电场定律 ②高斯磁场定律 ③法拉第感应定律 ④安培环路定律（含位移电流）。统一了电学、磁学和光学。",
        "advanced": "积分形式：∮E·dA=Q/ε₀, ∮B·dA=0, ∮E·dl=-dΦ_B/dt, ∮B·dl=μ₀(I+ε₀dΦ_E/dt)。微分形式：∇·E=ρ/ε₀, ∇·B=0, ∇×E=-∂B/∂t, ∇×B=μ₀J+μ₀ε₀∂E/∂t。预言电磁波，波速c=1/√(μ₀ε₀)。",
        "formulas": ["∇·E = ρ/ε₀", "∇·B = 0", "∇×E = -∂B/∂t", "∇×B = μ₀J + μ₀ε₀∂E/∂t", "c = 1/√(μ₀ε₀)"],
        "related": ["电磁感应", "电磁波", "光的电磁理论"],
        "applications": {
            "daily": "WiFi/蓝牙/手机信号的电磁波传播",
            "engineering": "天线设计；电磁兼容（EMC）分析；雷达系统",
            "research": "电磁场数值模拟（FDTD有限时域差分法）；超材料电磁波操控"
        },
        "exam_probability": 4,
        "common_types": ["概念题", "推导题", "综合题"],
        "contrast": {
            "概念A": "静电场",
            "A说明": "∇×E=0，电场无旋，可引入电势",
            "概念B": "变化磁场产生的电场",
            "B说明": "∇×E=-∂B/∂t，电场有旋，不能只用势描述",
            "区别": "静电场是保守场，感应电场是非保守场。这是麦克斯韦方程组的关键创新"
        }
    },
    "电磁波": {
        "subject": "电磁学/波动光学",
        "basic": "电磁波是变化的电场和磁场互相激发产生的横波。在真空中以光速传播 c = 3×10⁸ m/s。E和B同相，E⊥B⊥k。电磁波能量用坡印廷矢量 S = E×H 描述。",
        "advanced": "电磁波谱（γ射线→X射线→紫外→可见光→红外→微波→无线电）。辐射压力 P = S/c。偶极辐射功率 P = μ₀p₀²ω⁴/12πc。趋肤深度 δ = √(2/ωμσ)。",
        "formulas": ["c = fλ", "c = 1/√(μ₀ε₀)", "S = E×H", "I = ⟨S⟩ = ½cε₀E₀²"],
        "related": ["麦克斯韦方程组", "光的干涉衍射", "光的偏振"],
        "applications": {
            "daily": "微波炉（2.45GHz电磁波加热食物中的水分子）；遥控器红外线",
            "engineering": "5G通信的毫米波技术；卫星通信的微波频段",
            "research": "太赫兹成像（安检/医学）；引力波探测用激光干涉"
        },
        "exam_probability": 3,
        "common_types": ["概念题", "计算题"],
        "contrast": None
    },
    "光的干涉": {
        "subject": "波动光学",
        "basic": "相干光叠加产生干涉：明纹 δ = mλ，暗纹 δ = (m+½)λ。双缝干涉：条纹间距 Δx = λD/d。薄膜干涉：光程差来自反射光半波损失和几何路径差。",
        "advanced": "等厚干涉（劈尖、牛顿环）：相邻条纹对应厚度差 λ/2n。迈克尔逊干涉仪：移动 λ/2 时条纹移动一条。多光束干涉（法布里-珀罗）。",
        "formulas": ["δ = mλ（干涉加强）", "Δx = λD/d（双缝）", "2nd = mλ（薄膜加强）", "Δd = λ/2（迈克尔逊）"],
        "related": ["波动", "光的衍射", "光的偏振"],
        "applications": {
            "daily": "肥皂泡上的彩色条纹（薄膜干涉）；CD/DVD表面的彩虹色",
            "engineering": "增透膜（λ/4膜层减少反射）；光学精密测量（迈克尔逊干涉仪测微小位移）",
            "research": "LIGO引力波探测（4km臂长的迈克尔逊干涉仪，精度10⁻¹⁸m）；光学相干断层扫描（OCT医学成像）"
        },
        "exam_probability": 3,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    "光的衍射": {
        "subject": "波动光学",
        "basic": "惠更斯-菲涅尔原理：波前上每一点都是次级子波源。单缝衍射暗纹条件 asinθ = mλ。圆孔衍射（爱里斑）：第一暗环 sinθ = 1.22λ/D。",
        "advanced": "瑞利判据：两物点恰可分辨时，一点的爱里斑中心与另一点的第一暗环重合。光栅方程 dsinθ = mλ。布拉格衍射：2dsinθ = nλ。",
        "formulas": ["asinθ = mλ（单缝暗纹）", "sinθ = 1.22λ/D（爱里斑）", "dsinθ = mλ（光栅）", "R = λ/Δλ = mN（光栅分辨本领）"],
        "related": ["光的干涉", "波动", "电磁波"],
        "applications": {
            "daily": "CD/DVD的彩虹色（反射光栅衍射）；眯眼看灯光有星芒（眼睫毛衍射）",
            "engineering": "光谱仪中的衍射光栅（分析物质成分）；X射线晶体衍射确定晶体结构",
            "research": "电子显微镜（电子波长极短，分辨率达原子级）；X射线自由电子激光的相干衍射成像"
        },
        "exam_probability": 3,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    # ── 热学 ──────────────────────────────────────────────────
    "热力学第零一定律": {
        "subject": "热学",
        "basic": "第零定律：若A与B热平衡、B与C热平衡，则A与C热平衡（温度概念的基石）。第一定律：ΔU = Q + W，能量守恒在热力学中的体现。内能增量=吸热+外界做功。",
        "advanced": "准静态过程的功 W = -∫PdV。焓 H = U + PV。热容 C_v = (∂U/∂T)_v, C_p = (∂H/∂T)_p。理想气体内能 U = (f/2)nRT。",
        "formulas": ["ΔU = Q + W", "W = -∫PdV", "U = (f/2)nRT（理想气体）", "C_v = (f/2)R"],
        "related": ["热力学第二定律", "理想气体状态方程", "热力学过程"],
        "applications": {
            "daily": "冰箱制冷：压缩机做功使制冷剂从低温吸热到高温放热",
            "engineering": "内燃机热效率分析（奥托循环/狄塞尔循环）；发电厂热力循环（朗肯循环）",
            "research": "超导量子比特的极低温制冷（稀释制冷机达mK量级）"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    "热力学第二定律": {
        "subject": "热学",
        "basic": "第二定律：热量不能自发地从低温传到高温（克劳修斯表述）；不能从单一热源吸热完全转化为功而不产生其他影响（开尔文-普朗克表述）。熵增原理：孤立系统熵永不减少。",
        "advanced": "卡诺定理：可逆热机效率最高 η = 1 - T_L/T_H。熵 S = ∫dQ_rev/T。统计熵 S = klnΩ（玻尔兹曼公式）。信息熵与热力学熵的联系。",
        "formulas": ["η = 1 - T_L/T_H（卡诺效率）", "dS ≥ dQ/T", "S = klnΩ", "ΔS_universe ≥ 0"],
        "related": ["热力学第零一定律", "理想气体", "统计物理"],
        "applications": {
            "daily": "热水自然变凉但凉水不会自动变热（熵增）；空调将室内热搬到室外需要做功",
            "engineering": "热机效率上限由卡诺效率决定；热电材料（Seebeck效应）温差发电",
            "research": "麦克斯韦妖与信息热力学；黑洞热力学（贝肯斯坦-霍金熵）"
        },
        "exam_probability": 4,
        "common_types": ["概念题", "证明题", "计算题"],
        "contrast": None
    },
    "理想气体": {
        "subject": "热学",
        "basic": "状态方程 PV = nRT。等温（PV=const）、等容（P/T=const）、等压（V/T=const）、绝热（PV^γ=const）过程。平均自由程 λ = 1/(√2πd²n)。",
        "advanced": "麦克斯韦速率分布：f(v)dv = 4π(m/2πkT)^{3/2}v²exp(-mv²/2kT)dv。最概然速率 v_p = √(2kT/m)，平均速率 v_avg = √(8kT/πm)，方均根速率 v_rms = √(3kT/m)。",
        "formulas": ["PV = nRT", "PV^γ = const（绝热）", "E_k = ½mv²_avg = (3/2)kT", "λ = 1/√2πd²n"],
        "related": ["热力学", "统计物理", "输运现象"],
        "applications": {
            "daily": "自行车胎在夏天容易爆（温度升高→压强增大）；高压锅加速煮熟（高压提高沸点）",
            "engineering": "气体液化（林德循环）；真空技术中的气体分子运动",
            "research": "玻色-爱因斯坦凝聚（极低温下大量原子占据同一量子态）"
        },
        "exam_probability": 3,
        "common_types": ["计算题", "图像分析"],
        "contrast": None
    },
    # ── 量子物理 ──────────────────────────────────────────────
    "黑体辐射与普朗克量子假设": {
        "subject": "量子物理",
        "basic": "黑体辐射实验曲线无法用经典理论解释（瑞利-金斯公式在紫外端发散——紫外灾难）。普朗克假设：电磁辐射的能量是量子化的 E = nhν，n为整数。从而导出普朗克公式。",
        "advanced": "普朗克辐射定律：u(ν,T)dν = (8πhν³/c³) · 1/(e^(hν/kT)-1) dν。维恩位移定律 λ_max T = b。斯特藩-玻尔兹曼定律 j = σT⁴。",
        "formulas": ["E = hν（能量量子）", "u(ν,T) = (8πhν³/c³)/(e^(hν/kT)-1)", "λ_maxT = 2.898×10⁻³m·K", "j = σT⁴"],
        "related": ["光电效应", "波粒二象性", "原子结构"],
        "applications": {
            "daily": "红外测温枪（测量物体热辐射）；电炉丝温度升高颜色从红变白",
            "engineering": "热成像仪（夜视）；LED色温设计；太阳能热发电",
            "research": "宇宙微波背景辐射（CMB，2.725K黑体辐射）为宇宙大爆炸提供证据"
        },
        "exam_probability": 3,
        "common_types": ["概念题", "计算题"],
        "contrast": {
            "概念A": "经典理论",
            "A说明": "能量连续，导致紫外灾难",
            "概念B": "普朗克量子假设",
            "B说明": "能量不连续，E=nhν，解释黑体辐射",
            "区别": "这是量子力学的起点，标志着经典物理到量子物理的转折"
        }
    },
    "光电效应": {
        "subject": "量子物理",
        "basic": "光照射金属表面时，电子吸收光子能量逸出。爱因斯坦光电方程：E_k_max = hν - W，其中W是逸出功。存在截止频率 ν₀ = W/h，低于此频率无光电效应。",
        "advanced": "光电效应无法用经典波动理论解释（波动理论认为光强越大电子动能越大，但实验表明电子动能只与频率有关）。验证了光量子（光子）的存在。光电流与光强成正比（光子数）。",
        "formulas": ["E_k_max = hν - W", "ν₀ = W/h", "p = h/λ（光子动量）", "E = hν = hc/λ"],
        "related": ["黑体辐射", "波粒二象性", "康普顿散射"],
        "applications": {
            "daily": "太阳能电池板（光电效应将光能转为电能）；自动门的光电传感器",
            "engineering": "光电倍增管（微弱光信号放大，用于粒子探测/医学成像）；数码相机CCD/CMOS传感器",
            "research": "多光子光电效应（超强飞秒激光）；光电子能谱（ARPES测量材料能带结构）"
        },
        "exam_probability": 3,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    "波粒二象性与德布罗意波": {
        "subject": "量子物理",
        "basic": "德布罗意假设：实物粒子也具有波动性，波长 λ = h/p = h/(mv)。电子衍射实验（戴维孙-革麦实验）证实了电子的波动性。波粒二象性是量子力学的核心概念。",
        "advanced": "德布罗意波的相速度 v_p = ω/k = E/p = c²/v > c（不是物理速度），群速度 v_g = dω/dk = v（粒子的实际速度）。不确定性原理 ΔxΔp ≥ ħ/2 来源于波粒二象性。",
        "formulas": ["λ = h/p（德布罗意波长）", "p = ħk", "E = ħω", "ΔxΔp ≥ ħ/2"],
        "related": ["光电效应", "不确定原理", "薛定谔方程"],
        "applications": {
            "daily": "电子显微镜利用电子的波动性（波长远小于可见光）达到原子级分辨率",
            "engineering": "透射电子显微镜（TEM）分辨率达0.1nm以下；电子束光刻制造芯片",
            "research": "中子衍射（探测磁性结构）；原子干涉仪（重力测量精度达10⁻⁹g）"
        },
        "exam_probability": 3,
        "common_types": ["概念题", "计算题"],
        "contrast": None
    },
    "不确定原理": {
        "subject": "量子物理",
        "basic": "海森堡不确定原理：不能同时精确测量一对共轭物理量。ΔxΔp ≥ ħ/2（位置与动量），ΔEΔt ≥ ħ/2（能量与时间）。不是测量仪器的限制，而是自然的本质。",
        "advanced": "从对易关系 [x̂, p̂] = iħ 推导。能量-时间不确定原理用于解释虚粒子和量子隧穿。在量子场论中与粒子寿命关联 Γτ ≈ ħ。",
        "formulas": ["ΔxΔp ≥ ħ/2", "ΔEΔt ≥ ħ/2", "[x̂, p̂] = iħ"],
        "related": ["波粒二象性", "薛定谔方程", "量子力学"],
        "applications": {
            "daily": "日常宏观物体不确定度极小，不影响测量（如球的位置和动量可同时精确测量）",
            "engineering": "扫描隧道显微镜利用ΔEΔt隧穿效应成像；量子密码学利用不确定原理保证安全",
            "research": "标准量子极限与压缩光（LIGO引力波探测器用压缩态超越SQL）"
        },
        "exam_probability": 3,
        "common_types": ["概念题", "定性分析"],
        "contrast": None
    },
    "薛定谔方程": {
        "subject": "量子物理",
        "basic": "一维含时薛定谔方程：iħ∂Ψ/∂t = -ħ²/2m · ∂²Ψ/∂x² + VΨ。定态方程：-ħ²/2m · d²ψ/dx² + Vψ = Eψ。波函数的模平方 |Ψ|² 表示概率密度。",
        "advanced": "无限深势阱（粒子被束缚在势阱中，能量量子化 E_n = n²π²ħ²/2mL²）。量子隧穿：粒子可以穿过势垒（经典力学不允许）。态叠加原理：|Ψ⟩ = Σc_n|ψ_n⟩。",
        "formulas": ["iħ∂Ψ/∂t = ĤΨ", "Ĥ = -ħ²/2m ∇² + V", "E_n = n²h²/8mL²（无限深势阱）", "∫|Ψ|²dx = 1（归一化）"],
        "related": ["不确定原理", "波粒二象性", "原子结构"],
        "applications": {
            "daily": "LED/激光器依赖量子阱结构中的量子化能级",
            "engineering": "隧道二极管（利用量子隧穿效应）；量子点显示技术（QD-OLED）",
            "research": "量子计算中的量子比特（超导/离子阱/光子）；拓扑绝缘体表面态"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "推导题"],
        "contrast": None
    },
    "原子结构与能级": {
        "subject": "量子物理/原子物理",
        "basic": "玻尔模型：电子在量子化轨道上运动，角动量 L = nħ。能级 E_n = -13.6/n² eV。氢原子光谱：1/λ = R(1/n²_f - 1/n²_i)。四个量子数：n,l,m_l,m_s。",
        "advanced": "精细结构（自旋-轨道耦合）和超精细结构（核自旋）。泡利不相容原理：同一原子中无两电子四个量子数全相同。洪德规则。选择定则 Δl = ±1。",
        "formulas": ["E_n = -13.6/n² eV", "R = 1.097×10⁷ m⁻¹", "L = nħ", "1/λ = R(1/n_f² - 1/n_i²)"],
        "related": ["薛定谔方程", "波粒二象性", "凝聚态物理"],
        "applications": {
            "daily": "霓虹灯（不同气体原子能级跃迁发不同颜色的光）；荧光棒",
            "engineering": "激光器（受激辐射放大）；原子钟（铯133跃迁定义秒的基准）",
            "research": "光镊（利用激光冷却和俘获原子）；里德伯原子（高激发态，量子计算候选）"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    # ── 半导体物理 ────────────────────────────────────────────
    "能带理论与半导体": {
        "subject": "半导体物理",
        "basic": "固体中原子能级分裂成能带。价带（价电子填充）和导带（自由电子填充）之间的间隙是禁带。导体禁带为零，半导体禁带较小（∼1eV），绝缘体禁带很大（>5eV）。",
        "advanced": "k空间中E(k)关系。有效质量 m* = ħ²/(d²E/dk²)。直接带隙和间接带隙半导体。状态密度 g(E) ∝ √E。费米-狄拉克分布 f(E) = 1/(1+e^{(E-E_F)/kT})。",
        "formulas": ["E_g = E_c - E_v（禁带宽度）", "n = ∫g_c(E)f(E)dE", "p = ∫g_v(E)(1-f(E))dE", "n·p = n_i²（热平衡）"],
        "related": ["原子结构", "PN结", "载流子输运"],
        "applications": {
            "daily": "电脑/手机的CPU和内存依赖半导体能带工程",
            "engineering": "MOSFET（金属-氧化物-半导体场效应管）；LED发光波长由禁带宽度决定 λ = hc/E_g",
            "research": "拓扑绝缘体（表面态受时间反演对称保护）；二维材料（石墨烯、过渡金属硫族化物）"
        },
        "exam_probability": 4,
        "common_types": ["概念题", "推导题"],
        "contrast": None
    },
    "PN结": {
        "subject": "半导体物理",
        "basic": "P型半导体（空穴多）和N型半导体（电子多）接触形成PN结。扩散运动导致耗尽层和内建电场。内建电势 V_bi = (kT/q)ln(N_A N_D/n_i²)。I-V特性：I = I₀(e^{qV/kT}-1)。",
        "advanced": "击穿机制：齐纳击穿（强电场隧穿）和雪崩击穿（碰撞电离）。变容二极管（耗尽层电容随偏压变化）。肖特基结（金属-半导体接触）。",
        "formulas": ["V_bi = (kT/q)ln(N_A N_D/n_i²)", "I = I₀(e^{qV/kT}-1)", "C_j ∝ 1/√(V_bi+V)"],
        "related": ["能带理论", "载流子输运", "光电器件"],
        "applications": {
            "daily": "手机充电器中的整流二极管（交流→直流）",
            "engineering": "太阳能电池（PN结光伏效应）；发光二极管LED；激光二极管",
            "research": "单光子雪崩二极管（SPAD，量子通信）；隧道二极管（负阻效应）"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "概念题"],
        "contrast": None
    },
    "载流子输运": {
        "subject": "半导体物理",
        "basic": "漂移电流：J_drift = q(nμ_n + pμ_p)E。扩散电流：J_diff = q(D_n∇n - D_p∇p)。爱因斯坦关系：D/μ = kT/q。连续性方程。",
        "advanced": "霍尔效应：I_B 磁场中产生横向霍尔电压 V_H = R_H·IB/d。迁移率 μ = qτ/m*。散射机制：声子散射（晶格振动）、电离杂质散射。速度饱和（高场下）。",
        "formulas": ["J_drift = σE = q(nμ_n+pμ_p)E", "J_diff = qD∇n", "D/μ = kT/q", "V_H = R_H·IB/d"],
        "related": ["PN结", "能带理论"],
        "applications": {
            "daily": "霍尔传感器（电动车转把检测磁场变化）",
            "engineering": "MOSFET的沟道载流子迁移率决定开关速度；磁阻存储器（MRAM）",
            "research": "量子霍尔效应（整数量子霍尔效应/分数量子霍尔效应）；自旋电子学"
        },
        "exam_probability": 4,
        "common_types": ["计算题", "推导题"],
        "contrast": None
    },
}


# ══════════════════════════════════════════════════════════════════
# 物理常数速查
# ══════════════════════════════════════════════════════════════════

PHYSICAL_CONSTANTS = {
    "光速 c": {"value": 2.99792458e8, "unit": "m/s", "desc": "真空中光速"},
    "普朗克常数 h": {"value": 6.62607015e-34, "unit": "J·s", "desc": "量子的基本作用量"},
    "约化普朗克常数 ħ": {"value": 1.054571817e-34, "unit": "J·s", "desc": "h/2π"},
    "玻尔兹曼常数 k": {"value": 1.380649e-23, "unit": "J/K", "desc": "热力学与统计物理基本常数"},
    "阿伏伽德罗常数 N_A": {"value": 6.02214076e23, "unit": "mol⁻¹", "desc": "1摩尔物质的粒子数"},
    "元电荷 e": {"value": 1.602176634e-19, "unit": "C", "desc": "质子电荷量"},
    "电子质量 m_e": {"value": 9.10938370e-31, "unit": "kg", "desc": "电子静止质量"},
    "质子质量 m_p": {"value": 1.67262192e-27, "unit": "kg", "desc": "质子静止质量"},
    "真空介电常数 ε₀": {"value": 8.854187818e-12, "unit": "F/m", "desc": "真空电容率"},
    "真空磁导率 μ₀": {"value": 4e-7 * 3.14159265359, "unit": "N/A²", "desc": "真空磁导率 (4π×10⁻⁷)"},
    "精细结构常数 α": {"value": 7.297352569e-3, "unit": "无量纲", "desc": "α = e²/(4πε₀ħc) ≈ 1/137"},
    "里德伯常数 R_∞": {"value": 1.0973731568e7, "unit": "m⁻¹", "desc": "氢原子光谱常数"},
    "玻尔半径 a₀": {"value": 5.2917721090e-11, "unit": "m", "desc": "氢原子基态轨道半径"},
    "斯特藩常数 σ": {"value": 5.670374419e-8, "unit": "W/(m²·K⁴)", "desc": "黑体辐射总功率"},
    "标准重力加速度 g": {"value": 9.80665, "unit": "m/s²", "desc": "地球表面重力加速度"},
    "标准大气压 atm": {"value": 1.01325e5, "unit": "Pa", "desc": "1个标准大气压"},
    "玻尔磁子 μ_B": {"value": 9.274010078e-24, "unit": "J/T", "desc": "电子磁矩的量子单位"},
}


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════

def is_physics_related(text: str) -> bool:
    """判断文本是否与大学物理相关"""
    physics_keywords = [
        # 力学
        "力", "牛顿", "加速度", "速度", "位移", "动量", "冲量", "功", "能", "动能", "势能",
        "摩擦", "弹力", "重力", "万有引力", "圆周", "向心", "角速度", "转动惯量", "力矩",
        "简谐", "振动", "弹簧", "单摆", "波", "频率", "周期", "振幅",
        # 电磁学
        "电荷", "电场", "磁场", "电势", "电压", "电流", "电阻", "电容", "电感", "电磁",
        "高斯", "安培", "法拉第", "楞次", "洛伦兹", "库仑", "毕奥", "萨伐尔",
        "麦克斯韦", "电磁波", "介电", "磁导率", "电通量", "磁通量", "感生", "自感", "互感",
        # 热学
        "热", "温度", "熵", "焓", "内能", "卡诺", "绝热", "等温", "等容", "等压",
        "理想气体", "压强", "体积", "热容", "热机", "制冷", "平均自由程",
        # 光学
        "光", "干涉", "衍射", "偏振", "折射", "反射", "透镜", "光栅", "波长", "相位",
        "相干", "薄膜", "牛顿环", "迈克尔逊", "爱里斑",
        # 量子
        "量子", "普朗克", "光子", "光电", "波粒", "德布罗意", "薛定谔", "不确定",
        "能级", "原子", "轨道", "自旋", "泡利", "波函数", "概率密度", "隧穿",
        # 半导体
        "半导体", "能带", "禁带", "导带", "价带", "PN结", "二极管", "晶体管",
        "载流子", "电子", "空穴", "迁移率", "扩散", "漂移", "耗尽层",
        # 通用物理名词
        "物理", "守恒", "能量", "场", "势", "通量", "梯度", "散度", "旋度",
        "SI单位", "单位换算", "量纲", "物理常数",
    ]
    text_lower = text.lower()
    for kw in physics_keywords:
        if kw.lower() in text_lower:
            return True
    return False


def check_physics_identity(text: str) -> dict:
    """
    检测题目是否与大物相关
    返回: {"is_physics": bool, "confidence": float, "likely_subject": str}
    """
    is_phy = is_physics_related(text)
    # 进一步判断似然科目
    subjects = []
    for name, kp in PHYSICS_KNOWLEDGE.items():
        if name[:2].lower() in text.lower():
            subjects.append(name)
    likely = subjects[0] if subjects else ("未知" if not is_phy else "大学物理")
    
    return {
        "is_physics": is_phy,
        "likely_subject": likely,
    }


def lookup_knowledge_point(name: str) -> Optional[dict]:
    """按名称查找知识点"""
    if name in PHYSICS_KNOWLEDGE:
        return {"name": name, **PHYSICS_KNOWLEDGE[name]}
    # 模糊匹配
    for key, val in PHYSICS_KNOWLEDGE.items():
        if name in key or key in name:
            return {"name": key, **val}
    return None


def get_knowledge_expansion(topic: str) -> str:
    """获取知识点扩展文本"""
    info = lookup_knowledge_point(topic)
    if not info:
        return f"📚 未找到「{topic}」的相关知识点，你可以输入知识点名称让我详细讲解"
    
    text = f"""
📚 **知识点扩展：{info['name']}**

▸ **基础层级**
{info['basic']}

▸ **进阶层级**
{info['advanced']}

▸ **关键公式**
```
{chr(10).join(f'  {f}' for f in info['formulas'])}
```

▸ **关联知识点**
"""
    text += "  " + "  →  ".join(info["related"])
    
    if info.get("contrast"):
        c = info["contrast"]
        text += f"""

▸ **概念对比**
  {c.get('概念A', '')}：{c.get('A说明', '')}
  {c.get('概念B', '')}：{c.get('B说明', '')}
  🔍 区别：{c.get('区别', '')}
"""
    
    text += """

📖 想深入哪个？回复知识点名称即可
"""
    return text


def get_real_world_applications(topic: str) -> str:
    """获取现实应用"""
    info = lookup_knowledge_point(topic)
    if not info:
        return ""
    
    apps = info.get("applications", {})
    text = f"""
🌍 **现实中的落地：{info['name']}**

▸ 日常观察层面
{apps.get('daily', '（暂无）')}

▸ 工程应用层面
{apps.get('engineering', '（暂无）')}

▸ 科研前沿层面
{apps.get('research', '（暂无）')}

💡 想深入了解哪个方向？回复编号即可
"""
    return text


def generate_exam_variations(topic: str, difficulty: int = 1) -> str:
    """生成举一反三变式"""
    info = lookup_knowledge_point(topic)
    if not info:
        return ""
    
    formulas = info.get("formulas", [])
    base_formula = formulas[0] if formulas else ""
    
    variations = {
        "换条件": "",
        "换角度": "",
        "综合": "",
    }
    
    # 根据知识点不同生成不同的变式
    name = info["name"]
    if "高斯定理" in name:
        variations = {
            "换条件": f"【变式A·换条件】若电荷分布不是球对称而是柱对称（无限长带电圆柱），如何用高斯定理求电场？需要选择什么样的高斯面？",
            "换角度": f"【变式B·换角度】已知某区域电场分布 E = kr² r̂，能否反推出该区域的电荷体密度分布？",
            "综合": f"【变式C·综合】一带电球壳内外半径分别为R₁和R₂，总电荷Q均匀分布。①求各区域电场分布 ②求球壳内外的电势分布 ③求系统的静电能"
        }
    elif "牛顿" in name:
        variations = {
            "换条件": f"【变式A·换条件】若斜面和物体之间有摩擦系数 μ，物体从斜面顶端静止滑下，求到达底部时的速度",
            "换角度": f"【变式B·换角度】一个物体在光滑水平面上，受到随时间变化的力 F(t)=kt，求速度和位移随时间的变化",
            "综合": f"【变式C·综合】两个物体通过轻绳连接在滑轮两侧，斜面倾角θ，求①系统加速度 ②绳中张力 ③若斜面有摩擦，临界摩擦系数是多少？"
        }
    elif "电磁感应" in name:
        variations = {
            "换条件": f"【变式A·换条件】若磁场不是均匀变化而是 B(t)=B₀sin(ωt)，求线圈中的感应电动势及感应电流（线圈有电阻R和自感L）",
            "换角度": f"【变式B·换角度】一个导体棒在U形导轨上以速度v滑动，已知B均匀且垂直于导轨平面，求①棒中感应电动势 ②回路中的感应电流 ③维持匀速拉动所需的外力",
            "综合": f"【变式C·综合】矩形线圈在均匀磁场中绕垂直于B的轴以ω匀速转动，求①线圈中的感应电动势随时间的变化 ②线圈所受磁力矩 ③若线圈接入外阻R，求输出功率"
        }
    elif "光电" in name:
        variations = {
            "换条件": f"【变式A·换条件】若入射光波长变为原来的一半，逸出光电子的最大动能变为多少倍？",
            "换角度": f"【变式B·换角度】已知某金属的光电效应截止电压与入射光频率的关系 V₀ = 2.0×10⁻¹⁵ν - 4.0，求①普朗克常数 ②该金属的逸出功",
            "综合": f"【变式C·综合】一束单色光照在金属表面产生光电效应，同时产生X射线（轫致辐射），分析两个过程的能量关系"
        }
    else:
        variations = {
            "换条件": f"【变式A·换条件】如果题目中的已知条件互换（已知结果求参数），如何求解？",
            "换角度": f"【变式B·换角度】从能量角度/动量角度/对称性角度重新审视这个问题，是否有更简洁的解法？",
            "综合": f"【变式C·综合】将本题知识点与{info['related'][1] if len(info['related']) > 1 else '另一物理概念'}结合，设计一个综合题"
        }
    
    level_map = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆"}
    level_str = level_map.get(difficulty, "★★☆☆☆")
    
    text = f"""
🔄 **举一反三：{name}**
📊 难度：{level_str}

{variations['换条件']}

{variations['换角度']}

{variations['综合']}

💡 想练哪道变式？回复 A/B/C 即可
"""
    return text


def generate_mock_exam(subjects=None, num_questions=5, difficulty="medium") -> dict:
    """生成模拟考题（基于知识库随机出题）"""
    if subjects:
        candidates = {k: v for k, v in PHYSICS_KNOWLEDGE.items() 
                     if v.get("subject") in subjects}
    else:
        candidates = PHYSICS_KNOWLEDGE
    
    if not candidates:
        candidates = PHYSICS_KNOWLEDGE
    
    keys = random.sample(list(candidates.keys()), min(num_questions, len(candidates)))
    
    questions = []
    for k in keys:
        info = candidates[k]
        # 构造问题
        formulas = info.get("formulas", [])
        q = {
            "topic": k,
            "subject": info.get("subject", "大学物理"),
            "difficulty": info.get("exam_probability", 3),
            "question": f"请解释「{k}」的核心物理思想，并写出关键公式 {formulas[0] if formulas else ''}，说明其物理意义和适用条件。",
            "answer_hint": info["basic"][:100],
            "types": info.get("common_types", ["概念题"]),
        }
        questions.append(q)
    
    return {
        "title": "📋 大学物理模拟测验",
        "total": len(questions),
        "time": f"{len(questions) * 8}分钟",
        "questions": questions,
    }


def format_knowledge_response(topic: str, mode: str = "full") -> str:
    """
    生成完整的知识点响应（含扩展+现实+举一反三）
    mode: "full" / "expand" / "application" / "variation"
    """
    info = lookup_knowledge_point(topic)
    if not info:
        return f"抱歉，知识库中暂时没有「{topic}」的详细资料。你可以尝试输入：{', '.join(list(PHYSICS_KNOWLEDGE.keys())[:8])}"
    
    result = ""
    if mode in ("full", "expand"):
        result += get_knowledge_expansion(topic)
    if mode in ("full", "application"):
        result += get_real_world_applications(topic)
    if mode in ("full", "variation"):
        difficulty = min(info.get("exam_probability", 3) - 2, 4)
        result += generate_exam_variations(topic, max(1, difficulty))
    
    return result


# ══════════════════════════════════════════════════════════════════
# 物理常数查询
# ══════════════════════════════════════════════════════════════════

def search_constant(query: str) -> Optional[dict]:
    """查询物理常数"""
    for key, val in PHYSICAL_CONSTANTS.items():
        if query.lower() in key.lower() or query in val.get("desc", ""):
            return {"name": key, **val}
    return None


def list_all_constants() -> str:
    """列出所有物理常数"""
    lines = ["📐 **常用物理常数表**\n"]
    for name, info in PHYSICAL_CONSTANTS.items():
        val = info["value"]
        unit = info["unit"]
        desc = info["desc"]
        # 科学计数法格式化
        val_str = f"{val:.6e}" if abs(val) < 0.01 or abs(val) > 1e6 else str(val)
        lines.append(f"  {name} = {val_str} {unit}")
        lines.append(f"    └ {desc}")
    return "\n".join(lines)


def generate_exam_sprint_plan(scope: str, days: int = 3) -> str:
    """生成 3天速通计划"""
    
    plan_intro = f"""
🚀 **{days}天速通考试计划**
📌 范围：{scope}
📅 计划时长：{days}天

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    if days >= 1:
        plan_intro += """
**Day 1 📋 考点扫描**
  • AI自动提取考试范围内的核心考点
  • 按出题概率从高到低排序
  • 生成每考点的掌握度自测清单
  • 预计用时：2-3小时
"""
    if days >= 2:
        plan_intro += """
**Day 2 📝 题型专项**
  • 针对高频考点生成典型例题
  • 每题含完整解析和评分标准
  • 做完即时批改 + 错题收录
  • 预计用时：3-4小时
"""
    if days >= 3:
        plan_intro += """
**Day 3 🎯 模拟冲刺**
  • 全真模拟卷（按真实考试题型/分值配比）
  • 限时演练（计时器独立计时）
  • 自动批改 + 得分预估 + 薄弱点分析
  • 预计用时：2小时考试 + 1小时复盘
"""

    plan_intro += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 输入以下命令开始：
  /sprint day1   → 开始 Day 1 考点扫描
  /sprint day2   → 开始 Day 2 题型专项
  /sprint day3   → 开始 Day 3 模拟冲刺
  /sprint status → 查看当前进度
"""
    return plan_intro


# ══════════════════════════════════════════════════════════════════
# 错误记录（错题本）
# ══════════════════════════════════════════════════════════════════

import os as _os

ERROR_NOTEBOOK_DIR = _os.path.join(_os.path.expanduser("~"), ".smart-tutor", "error_notebook")
if not _os.path.exists(ERROR_NOTEBOOK_DIR):
    _os.makedirs(ERROR_NOTEBOOK_DIR, exist_ok=True)


def _error_book_path() -> str:
    return _os.path.join(ERROR_NOTEBOOK_DIR, "errors.jsonl")


def add_error_record(question: str, user_answer: str, correct_answer: str, 
                     error_reason: str = "", topic: str = "", source: str = "web"):
    """添加错题记录"""
    import json, time
    record = {
        "id": int(time.time() * 1000),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question[:200],
        "user_answer": user_answer[:200],
        "correct_answer": correct_answer[:500],
        "error_reason": error_reason[:200],
        "topic": topic,
        "source": source,
        "reviewed": False,
        "mastered": False,
    }
    with open(_error_book_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def get_error_notebook(topic: str = "", error_type: str = "") -> list:
    """获取错题本记录，支持按知识点/错误类型筛选"""
    records = []
    if not _os.path.exists(_error_book_path()):
        return records
    
    import json
    with open(_error_book_path(), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if topic and topic not in r.get("topic", "") and topic not in r.get("error_reason", ""):
                    continue
                if error_type and error_type not in r.get("error_reason", ""):
                    continue
                records.append(r)
            except:
                pass
    
    return records


def get_error_stats() -> dict:
    """获取错题本统计信息"""
    records = get_error_notebook()
    if not records:
        return {"total": 0, "by_topic": {}, "by_reason": {}, "mastered": 0}
    
    by_topic = {}
    by_reason = {}
    for r in records:
        t = r.get("topic", "未知")
        by_topic[t] = by_topic.get(t, 0) + 1
        reason = r.get("error_reason", "未知")
        # 简化错误类型
        for kw in ["公式", "符号", "单位", "方向", "计算", "概念"]:
            if kw in reason:
                by_reason[kw] = by_reason.get(kw, 0) + 1
                break
        else:
            by_reason["其他"] = by_reason.get("其他", 0) + 1
    
    return {
        "total": len(records),
        "by_topic": dict(sorted(by_topic.items(), key=lambda x: -x[1])),
        "by_reason": dict(sorted(by_reason.items(), key=lambda x: -x[1])),
        "mastered": sum(1 for r in records if r.get("mastered")),
    }


def format_error_notebook(topic: str = "") -> str:
    """格式化输出错题本"""
    records = get_error_notebook(topic)
    stats = get_error_stats()
    
    if not records:
        return "📓 **错题本** 📓\n\n暂无错题记录！继续保持 ✨"
    
    text = f"""
📓 **错题本** 📓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 统计：共 {stats['total']} 题 | 已掌握 {stats['mastered']} 题

📂 按知识点分布：
"""
    for topic_name, count in stats.get("by_topic", {}).items():
        bar = "█" * min(count, 10) + ("★" * min(count, 5) if count > 10 else "")
        text += f"  {topic_name}: {count}题 {bar}\n"
    
    text += "\n❌ 常见错误类型：\n"
    for reason, count in stats.get("by_reason", {}).items():
        text += f"  {reason}: {count}次\n"
    
    if records:
        text += "\n📝 最近错题：\n"
        for r in records[-5:]:
            text += f"  🕐 {r.get('time','')} | {r.get('question','')[:40]}...\n"
        text += f"\n（共 {len(records)} 条记录，输入 /error clear 清空，/error review <题号> 标记已掌握）\n"
    
    return text


# ══════════════════════════════════════════════════════════════════
# 创新功能模块：7大功能
# ══════════════════════════════════════════════════════════════════

import time as _time

# ── 科目知识链（用于一题通全章） ─────────────────────────────

SUBJECT_CHAINS = {
    "电磁学": [
        "库仑定律与电场",
        "高斯定理",
        "电势与电势差",
        "电容与电容器",
        "静电场中的导体",
        "恒磁场与毕奥-萨伐尔定律",
        "安培环路定理",
        "电磁感应",
        "麦克斯韦方程组",
        "电磁波",
    ],
    "力学": [
        "牛顿运动定律",
        "受力分析",
        "功与能",
        "动量守恒",
        "圆周运动与万有引力",
        "简谐振动",
        "波动",
    ],
    "热学": [
        "热力学第零一定律",
        "理想气体",
        "热力学第二定律",
    ],
    "量子物理": [
        "黑体辐射与普朗克量子假设",
        "光电效应",
        "波粒二象性与德布罗意波",
        "不确定原理",
        "薛定谔方程",
        "原子结构与能级",
    ],
    "波动光学": [
        "光的干涉",
        "光的衍射",
        "电磁波",
    ],
    "半导体物理": [
        "能带理论与半导体",
        "PN结",
        "载流子输运",
    ],
}


# ══════════════════════════════════════════════════════════════════
# 功能1：一题通全章 (Chain Question)
# ══════════════════════════════════════════════════════════════════

def list_available_chains() -> list:
    """列出所有可用的科目链"""
    return list(SUBJECT_CHAINS.keys())


def generate_chain_question(subject: str) -> dict:
    """
    生成一道贯穿整个章节的综合题。
    
    参数:
        subject: 科目名（如 "电磁学", "力学"）
    
    返回:
        dict: {title, description, steps: [{name, concept, question, hint}]}
    """
    if subject not in SUBJECT_CHAINS:
        available = list_available_chains()
        return {
            "title": f"❌ 未找到科目「{subject}」",
            "description": f"可用科目：{'、'.join(available)}",
            "steps": [],
        }
    
    chain_keys = SUBJECT_CHAINS[subject]
    steps = []
    
    for key in chain_keys:
        kp = PHYSICS_KNOWLEDGE.get(key)
        if not kp:
            continue
        
        formulas = kp.get("formulas", [])
        formula_str = formulas[0] if formulas else ""
        
        # 根据知识点类型生成有意义的 step 问题
        if "库仑" in key:
            question = f"两个点电荷 q₁=+2×10⁻⁶C 和 q₂=-3×10⁻⁶C 相距 r=0.3m，求它们之间的库仑力大小和方向。"
            hint = f"使用库仑公式 {formula_str}，注意力的方向：同号相斥、异号相吸"
        elif "高斯" in key:
            question = f"一个半径为R的均匀带电球壳，总电荷为Q。利用高斯定理求球壳外(r>R)的电场分布。"
            hint = f"选择同心球面作为高斯面，利用对称性：{formula_str}"
        elif "电势" in key:
            question = f"在上题求得的电场分布基础上，求球壳外距离球心r处的电势（取无穷远处电势为零）。"
            hint = f"电势与电场的关系：{formulas[0] if formulas else 'V_ab = -∫E·dl'}"
        elif "电容" in key:
            question = f"若将上述带电球壳与一个平行板电容器（板间距d=0.01m，面积S=0.1m²）并联，求等效电容。"
            hint = f"球壳电容 C=4πε₀R，平行板电容 {formula_str}"
        elif "静电场中的导体" in key:
            question = f"将一个不带电的导体球壳放入上述电场中，达到静电平衡后，球壳内部的电场强度是多少？球壳表面的电荷如何分布？"
            hint = f"静电平衡条件：{formulas[0] if formulas else 'E_inside = 0'}"
        elif "毕奥" in key or "恒磁场" in key:
            question = f"一根无限长直导线通有电流 I=5A，求距离导线 r=0.1m 处的磁感应强度大小和方向。"
            hint = f"使用毕奥-萨伐尔定律的简化形式：{formula_str}"
        elif "安培环路" in key:
            question = f"一根无限长载流圆柱导体（半径R，电流I均匀分布），用安培环路定理求导体内部(r<R)和外部的磁场分布。"
            hint = f"选择圆形安培环路：{formula_str}"
        elif "电磁感应" in key:
            question = f"一个矩形线圈(边长a=0.2m, b=0.3m)置于上述导线旁的磁场中，若线圈以速度v=2m/s远离导线，求线圈中的感应电动势。"
            hint = f"法拉第电磁感应定律：{formula_str}"
        elif "麦克斯韦" in key:
            question = f"在上一问的电磁感应过程中，说明麦克斯韦方程组中哪些方程在起作用？变化的磁场如何产生电场？"
            hint = f"法拉第定律的微分形式：∇×E = -∂B/∂t"
        elif "电磁波" in key:
            question = f"上述电磁振荡产生的电磁波在真空中传播，求其波长（若频率f=10⁸Hz）。电磁波中E和B的相位关系如何？"
            hint = f"波速公式：{formulas[0] if formulas else 'c = fλ'}"
        elif "牛顿" in key:
            question = f"一个质量 m=2kg 的物体在光滑水平面上受到水平拉力 F=10N，求物体的加速度。"
            hint = f"牛顿第二定律：{formula_str}"
        elif "受力分析" in key:
            question = f"将上述物体放在倾角 θ=30° 的斜面上（有摩擦系数 μ=0.2），画出受力分析图并求加速度。"
            hint = f"正交分解重力，沿斜面方向列牛顿第二定律"
        elif "功与能" in key:
            question = f"物体从斜面顶端（高h=2m）由静止滑下，求到达底部时的速度（用功能原理）。"
            hint = f"动能定理：{formulas[-1] if formulas else 'W = ΔE_k'}"
        elif "动量" in key:
            question = f"若上述物体到达底部后与一个静止物体（m₂=1kg）发生完全非弹性碰撞，求碰撞后两物体的共同速度。"
            hint = "动量守恒：" + (formulas[2] if len(formulas) > 2 else "m₁v₁+m₂v₂ = m₁v₁'+m₂v₂'")
        elif "圆周" in key or "万有引力" in key:
            question = f"将两个物体视为双星系统（质量分别为m₁和m₂），它们绕质心做圆周运动，推导轨道半径和周期的关系。"
            hint = f"万有引力提供向心力：{formula_str}"
        elif "简谐" in key:
            question = f"一个弹簧振子（k=100N/m, m=0.5kg）从平衡位置拉开 A=0.1m 后释放，求振动周期和运动方程。"
            hint = f"简谐振动公式：{formula_str}"
        elif "波动" in key:
            question = f"上述振子在介质中激发平面简谐波，波速 v=340m/s，写出波的表达式并求相邻波节之间的距离。"
            hint = f"波速与波长的关系：{formulas[0] if formulas else 'v = λf'}"
        elif "热力学第零" in key or "热力学第一" in key or "热力学第零一" in key:
            question = f"一定量的理想气体（n=2mol）从初态(T₁=300K, V₁=0.05m³)经等温膨胀到 V₂=0.10m³，求气体对外做功和吸收的热量。"
            hint = f"热力学第一定律：{formula_str}，等温过程 ΔU=0"
        elif "理想气体" in key:
            question = f"求上述气体在初态时的压强，以及等温膨胀后的末态压强。"
            hint = f"理想气体状态方程：{formula_str}"
        elif "热力学第二" in key:
            question = f"若上述等温膨胀过程是可逆的，求气体的熵变。判断该过程是否违背热力学第二定律。"
            hint = f"熵的定义：dS = dQ_rev/T，热力学第二定律要求孤立系统熵不减"
        elif "黑体辐射" in key or "普朗克" in key:
            question = f"某黑体的温度 T=5000K，求其辐射峰值波长。该黑体单位面积的辐射总功率是多少？"
            hint = f"维恩位移定律：λ_max·T = b，斯特藩-玻尔兹曼定律：j=σT⁴"
        elif "光电效应" in key:
            question = f"用 λ=300nm 的紫外线照射逸出功 W=2.3eV 的金属表面，求逸出光电子的最大动能。"
            hint = f"爱因斯坦光电方程：{formula_str}"
        elif "德布罗意" in key or "波粒" in key:
            question = f"求上述逸出光电子的德布罗意波长。说明电子的波动性如何被实验证实。"
            hint = f"德布罗意关系：{formula_str}"
        elif "不确定" in key:
            question = f"若上述电子的位置不确定度 Δx=0.1nm，求其动量不确定度的最小值。"
            hint = f"海森堡不确定原理：{formula_str}"
        elif "薛定谔" in key:
            question = f"将电子视为一维无限深势阱中的粒子（阱宽 L=0.5nm），求电子的基态能量。"
            hint = f"无限深势阱能级公式：{formulas[2] if len(formulas) > 2 else 'E_n = n²h²/8mL²'}"
        elif "原子结构" in key or "能级" in key:
            question = f"氢原子从 n=3 能级跃迁到 n=2 能级，求辐射光子的波长和频率。该波长属于哪个光谱线系？"
            hint = f"里德伯公式：{formulas[-1] if formulas else '1/λ = R(1/n_f² - 1/n_i²)'}"
        elif "干涉" in key:
            question = f"杨氏双缝干涉实验中，双缝间距 d=0.5mm，屏距缝 D=1m，用 λ=589nm 的钠黄光照射，求相邻明纹间距。"
            hint = f"双缝干涉条纹间距：{formulas[1] if len(formulas) > 1 else 'Δx = λD/d'}"
        elif "衍射" in key:
            question = f"在上述实验中的一个缝后用 λ=589nm 做单缝衍射，缝宽 a=0.1mm，求中央明纹的宽度。"
            hint = f"单缝衍射暗纹条件：{formula_str}"
        elif "能带" in key or "半导体" in key:
            question = f"硅的禁带宽度 E_g=1.12eV，计算其在 T=300K 时的本征载流子浓度（已知 n_i²=N_c N_v exp(-E_g/kT)）。"
            hint = f"本征半导体中 n=p=n_i，n_i 依赖于禁带宽度和温度"
        elif "PN结" in key:
            question = f"硅PN结的 N_A=10¹⁷cm⁻³，N_D=10¹⁵cm⁻³，T=300K，求内建电势 V_bi。"
            hint = f"内建电势公式：{formula_str}"
        elif "载流子" in key:
            question = f"在上述PN结上加正向偏压 V=0.5V，求注入的少数载流子浓度。电子和空穴的扩散电流方向如何？"
            hint = f"少子注入：p_n = p_n₀·e^{qV/kT}"
        else:
            question = f"请详细解释「{key}」的核心物理原理，并写出关键公式。"
            hint = f"参考{key}的基本概念和公式"
        
        steps.append({
            "name": key,
            "concept": kp.get("advanced", kp.get("basic", ""))[:80],
            "question": question,
            "hint": hint,
        })
    
    if not steps:
        return {
            "title": f"❌ 科目「{subject}」的知识点链为空",
            "description": "请检查知识库中该科目下的知识点",
            "steps": [],
        }
    
    # 生成描述文本
    chain_names = " → ".join(s["name"] for s in steps)
    description = (
        f"📚 **一题通全章：{subject}**\n\n"
        f"这道综合题将带你串联 {subject} 的全部核心知识点：\n"
        f"🔗 {chain_names}\n\n"
        f"从基础到综合，每步都有提示，做完一题 = 复习一章！"
    )
    
    return {
        "title": f"📚 一题通全章 · {subject}",
        "description": description,
        "steps": steps,
    }


# ══════════════════════════════════════════════════════════════════
# 功能2：Boss战模式 (Boss Mode)
# ══════════════════════════════════════════════════════════════════

BOSS_SESSIONS = {}  # 全局 Boss 会话存储

_BOSS_NAMES = {
    "力学": "牛顿爵士 · 力学领主",
    "电磁学": "麦克斯韦 · 电磁之王",
    "热学": "卡诺勋爵 · 熵之守护者",
    "波动光学": "菲涅尔 · 光之仲裁者",
    "量子物理": "薛定谔 · 量子幽灵",
    "半导体物理": "肖克利 · 硅晶巨人",
}


def _generate_session_id() -> str:
    return f"boss_{int(_time.time() * 1000)}_{random.randint(1000, 9999)}"


def start_boss_session(subject: str) -> dict:
    """
    开始一个 Boss 战会话。
    
    参数:
        subject: 科目名
    
    返回:
        dict: {session_id, boss_name, minibosses: [...], total_exp, unlock_level}
    """
    if subject not in SUBJECT_CHAINS:
        available = list_available_chains()
        return {
            "session_id": "",
            "boss_name": "未知领域",
            "minibosses": [],
            "total_exp": 0,
            "unlock_level": 0,
            "error": f"❌ 未知科目「{subject}」，可用科目：{'、'.join(available)}",
        }
    
    session_id = _generate_session_id()
    chain_keys = SUBJECT_CHAINS[subject]
    boss_name = _BOSS_NAMES.get(subject, f"{subject} · 知识守护者")
    
    minibosses = []
    total_exp = 0
    for i, key in enumerate(chain_keys):
        kp = PHYSICS_KNOWLEDGE.get(key)
        if not kp:
            continue
        prob = kp.get("exam_probability", 3)
        difficulty = min(i + 1, 5)  # 难度随进度递增
        reward_exp = 10 + i * 5 + prob * 3
        
        # 根据知识类型生成不同的小怪问题
        formulas = kp.get("formulas", [])
        f_str = formulas[0] if formulas else ""
        
        if i == 0:
            question = f"【基础热身】请简述「{key}」的核心概念。"
        elif prob >= 5:
            question = f"【核心考点】请写出 {key} 的关键公式 {f_str} 并说明其物理意义和适用条件。"
        elif i == len(chain_keys) - 1:
            question = f"【终极小怪】{key}：请结合前面学过的知识点，分析该知识的综合应用。"
        else:
            question = f"【进阶挑战】利用 {f_str} 解决一个关于 {key} 的实际问题。"
        
        miniboss = {
            "id": f"mb_{session_id}_{i}",
            "topic": key,
            "question": question,
            "difficulty": difficulty,
            "reward_exp": reward_exp,
        }
        minibosses.append(miniboss)
        total_exp += reward_exp
    
    boss_session = {
        "session_id": session_id,
        "subject": subject,
        "boss_name": boss_name,
        "minibosses": minibosses,
        "total_exp": total_exp,
        "unlock_level": len(minibosses),
        "completed_mb": set(),
        "boss_unlocked": False,
        "started_at": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    BOSS_SESSIONS[session_id] = boss_session
    
    return {
        "session_id": session_id,
        "boss_name": boss_name,
        "minibosses": [
            {"id": m["id"], "topic": m["topic"], "question": m["question"],
             "difficulty": m["difficulty"], "reward_exp": m["reward_exp"]}
            for m in minibosses
        ],
        "total_exp": total_exp,
        "unlock_level": boss_session["unlock_level"],
    }


def fight_miniboss(session_id: str, miniboss_id: str) -> dict:
    """
    挑战小怪（返回题目和提示）。
    
    参数:
        session_id: 会话ID
        miniboss_id: 小怪ID
    
    返回:
        dict: {question, hint, answer_check_template}
    """
    session = BOSS_SESSIONS.get(session_id)
    if not session:
        return {"error": "❌ 会话不存在或已过期，请重新开始游戏 /boss start <科目>"}
    
    target = None
    for mb in session["minibosses"]:
        if mb["id"] == miniboss_id:
            target = mb
            break
    
    if not target:
        return {"error": f"❌ 未找到小怪 {miniboss_id}"}
    
    if miniboss_id in session.get("completed_mb", set()):
        return {"warning": "⚠️ 这个小怪已经被击败了！挑战下一个吧~", "question": target["question"]}
    
    topic_info = PHYSICS_KNOWLEDGE.get(target["topic"], {})
    formulas = topic_info.get("formulas", [])
    advanced = topic_info.get("advanced", "")
    
    hint = advanced[:150] if advanced else f"回忆「{target['topic']}」相关概念"
    if formulas:
        hint += f"\n关键公式参考：{'；'.join(formulas)}"
    
    return {
        "question": target["question"],
        "hint": hint,
        "answer_check_template": f"请提交你的答案，系统将根据「{target['topic']}」的核心概念进行评分",
    }


def _mark_miniboss_defeated(session_id: str, miniboss_id: str) -> dict:
    """标记小怪已击败（内部调用）"""
    session = BOSS_SESSIONS.get(session_id)
    if not session:
        return None
    
    session["completed_mb"].add(miniboss_id)
    
    # 检查是否所有小怪都打完了
    all_ids = {m["id"] for m in session["minibosses"]}
    if session["completed_mb"] == all_ids:
        session["boss_unlocked"] = True
    
    # 计算已获得经验
    exp = 0
    for mb in session["minibosses"]:
        if mb["id"] in session["completed_mb"]:
            exp += mb["reward_exp"]
    
    return {
        "session_id": session_id,
        "exp_earned": exp,
        "minibosses_complete": len(session["completed_mb"]),
        "total_minibosses": len(session["minibosses"]),
        "boss_unlocked": session["boss_unlocked"],
    }


def fight_boss(session_id: str) -> dict:
    """
    挑战 Boss（所有小怪击败后方可挑战）。
    
    参数:
        session_id: 会话ID
    
    返回:
        dict: {boss_question, all_topics_integrated}
    """
    session = BOSS_SESSIONS.get(session_id)
    if not session:
        return {"error": "❌ 会话不存在或已过期，请重新开始游戏 /boss start <科目>"}
    
    if not session.get("boss_unlocked"):
        remaining = len(session["minibosses"]) - len(session.get("completed_mb", set()))
        return {"error": f"🔒 Boss 尚未解锁！还需要击败 {remaining} 个小怪才能挑战 Boss！"}
    
    subject = session["subject"]
    chain_keys = SUBJECT_CHAINS.get(subject, [])
    
    topics_integrated = []
    for key in chain_keys:
        kp = PHYSICS_KNOWLEDGE.get(key, {})
        topics_integrated.append(f"{key}（{kp.get('exam_probability', 3)}★）")
    
    boss_name = session["boss_name"]
    boss_question = (
        f"👑 **最终 Boss：{boss_name}**\n\n"
        f"欢迎来到最终挑战！你需要综合运用 {subject} 的全部知识解决以下综合大题：\n\n"
    )
    
    if subject == "电磁学":
        boss_question += (
            "【综合大题】一个半径为R的金属球壳带有总电荷Q，球壳外距离球心r处有一正点电荷q。\n\n"
            "请回答：\n"
            "(1) 求球壳内外的电场分布（使用高斯定理）\n"
            "(2) 求球壳表面和内部任意点的电势\n"
            "(3) 若将球壳接地，球壳上的电荷分布如何变化？\n"
            "(4) 若让球壳绕直径以角速度ω旋转，求球心处的磁感应强度\n"
            "(5) 若上述磁场随时间变化，说明会产生什么物理效应\n"
        )
    elif subject == "力学":
        boss_question += (
            "【综合大题】一个弹簧振子（k=200N/m, m=0.5kg）放置在倾角30°的粗糙斜面上（μ=0.1），\n"
            "初始时将弹簧压缩0.2m后释放。\n\n"
            "请回答：\n"
            "(1) 画出物体的受力分析图并写出运动方程\n"
            "(2) 求刚释放时物体的加速度\n"
            "(3) 用能量方法求物体通过平衡位置时的速度\n"
            "(4) 若物体到达斜面底端时与一个静止物体发生完全弹性碰撞，分析碰撞后的运动\n"
            "(5) 整个过程中机械能是否守恒？为什么？\n"
        )
    elif subject == "热学":
        boss_question += (
            "【综合大题】2mol 理想气体经历以下循环：\n"
            "A→B: 等温膨胀（T₁=400K, V_A=0.02m³ → V_B=0.04m³）\n"
            "B→C: 等容降压（V_C=V_B, T_C=300K）\n"
            "C→A: 等压压缩（回到初态）\n\n"
            "请回答：\n"
            "(1) 求各过程中气体做的功、吸收的热量和内能变化\n"
            "(2) 求该循环的效率\n"
            "(3) 计算整个循环的熵变\n"
            "(4) 该循环是否满足热力学第二定律？为什么？\n"
        )
    elif subject == "波动光学":
        boss_question += (
            "【综合大题】一束波长为589nm的平行光垂直照射到双缝上（缝距d=0.5mm），\n"
            "屏距缝D=1m。在其中一个缝后放置一块厚度为e=1μm、折射率n=1.5的薄膜。\n\n"
            "请回答：\n"
            "(1) 未放薄膜时的条纹间距是多少？\n"
            "(2) 放置薄膜后，零级明纹如何移动？移动多少条？\n"
            "(3) 若将双缝换成单缝（缝宽a=0.1mm），中央明纹的宽度是多少？\n"
            "(4) 若再在缝后放光栅（N=500条/mm），求第一级主极大的衍射角\n"
            "(5) 分析光栅的分辨本领与哪些因素有关\n"
        )
    elif subject == "量子物理":
        boss_question += (
            "【综合大题】一个电子被束缚在一维无限深势阱中（阱宽L=0.2nm），\n"
            "初始时处于基态。\n\n"
            "请回答：\n"
            "(1) 求电子的基态能量和第一激发态能量\n"
            "(2) 若用波长为λ的光照射，电子吸收光子从基态跃迁到第一激发态，求λ\n"
            "(3) 求基态电子的德布罗意波长\n"
            "(4) 若将势阱宽度缩小为原来的一半，基态能量如何变化？解释物理原因\n"
            "(5) 说明不确定原理如何解释上述能级变化\n"
        )
    elif subject == "半导体物理":
        boss_question += (
            "【综合大题】一硅PN结在T=300K下工作，N_A=10¹⁷cm⁻³, N_D=10¹⁵cm⁻³，\n"
            "硅的禁带宽度E_g=1.12eV。\n\n"
            "请回答：\n"
            "(1) 求内建电势V_bi和耗尽层宽度\n"
            "(2) 画出平衡状态下的能带图（标出费米能级位置）\n"
            "(3) 求正向偏压V=0.6V时的注入电流密度\n"
            "(4) 当反向偏压增大到一定程度时会发生什么现象？说明两种击穿机制\n"
            "(5) 该PN结受光照时会产生什么效应？说明其在太阳能电池中的应用\n"
        )
    else:
        boss_question += (
            f"【综合大题】请综合运用 {subject} 的全部核心知识点，\n"
            f"解决一个包含以下所有主题的综合问题：{'、'.join(chain_keys)}\n\n"
            "请展示你的推理过程，标注每一步用到的物理原理和公式。"
        )
    
    return {
        "boss_question": boss_question,
        "all_topics_integrated": topics_integrated,
    }


def get_boss_progress(session_id: str) -> dict:
    """获取 Boss 战进度"""
    session = BOSS_SESSIONS.get(session_id)
    if not session:
        return {"error": "❌ 会话不存在或已过期"}
    
    total = len(session["minibosses"])
    completed = len(session.get("completed_mb", set()))
    
    exp = 0
    for mb in session["minibosses"]:
        if mb["id"] in session.get("completed_mb", set()):
            exp += mb["reward_exp"]
    
    return {
        "session_id": session_id,
        "subject": session["subject"],
        "boss_name": session["boss_name"],
        "minibosses_complete": completed,
        "total_minibosses": total,
        "exp_earned": exp,
        "boss_unlocked": session.get("boss_unlocked", False),
        "progress_bar": "█" * completed + "░" * (total - completed),
        "started_at": session.get("started_at", ""),
    }


# ══════════════════════════════════════════════════════════════════
# 功能3：考试热点预测 (Exam Prediction)
# ══════════════════════════════════════════════════════════════════

def predict_exam_topics(subject: str = "", top_n: int = 10) -> dict:
    """
    基于知识库的统计预测高频考点。
    
    参数:
        subject: 科目筛选（空=全部）
        top_n: 返回前N个热点
    
    返回:
        dict: {subject, predictions: [...], analysis: str}
    """
    candidates = []
    for name, kp in PHYSICS_KNOWLEDGE.items():
        if subject and kp.get("subject", "") != subject:
            continue
        prob = kp.get("exam_probability", 1)
        probability = prob / 5.0  # 转换为 0-1
        stars = "★" * prob + "☆" * (5 - prob)
        
        candidates.append({
            "topic": name,
            "subject": kp.get("subject", ""),
            "probability": round(probability, 2),
            "stars": stars,
            "common_types": kp.get("common_types", []),
        })
    
    # 按 probability 降序排列
    candidates.sort(key=lambda x: -x["probability"])
    
    predictions = candidates[:top_n]
    
    # 生成分析文本
    must_know = [p["topic"] for p in predictions if p["probability"] >= 0.8]
    likely = [p["topic"] for p in predictions if 0.6 <= p["probability"] < 0.8]
    possible = [p["topic"] for p in predictions if 0.4 <= p["probability"] < 0.6]
    
    lines = ["📊 **考试热点预测分析**\n"]
    
    if must_know:
        lines.append(f"🔴 **几乎必考（概率≥80%）**：")
        lines.append(f"   {'、'.join(must_know)}")
        lines.append("")
    
    if likely:
        lines.append(f"🟡 **高概率考点（60%~80%）**：")
        lines.append(f"   {'、'.join(likely)}")
        lines.append("")
    
    if possible:
        lines.append(f"🟢 **可能考察（40%~60%）**：")
        lines.append(f"   {'、'.join(possible)}")
        lines.append("")
    
    if must_know:
        lines.append("💡 **复习建议**：优先掌握必考知识点，再扩展到高频考点。")
        lines.append(f"    其中「{must_know[0]}」是重中之重，建议配合典型例题深入练习。")
    else:
        lines.append("💡 **复习建议**：均匀覆盖所有知识点，重点练习计算题和综合题。")
    
    if subject:
        lines.append(f"\n📌 当前筛选科目：{subject}")
    
    if not candidates:
        return {
            "subject": subject,
            "predictions": [],
            "analysis": f"❌ 未找到科目「{subject}」的知识点",
        }
    
    return {
        "subject": subject if subject else "全部科目",
        "predictions": predictions,
        "analysis": "\n".join(lines),
    }


# ══════════════════════════════════════════════════════════════════
# 功能4：物理盲点探测器 (Blindspot Detector)
# ══════════════════════════════════════════════════════════════════

_ERROR_TYPE_KEYWORDS = {
    "公式记错": ["公式", "写错", "记错公式", "混淆"],
    "符号/方向": ["符号", "方向", "正负", "矢量"],
    "单位换算": ["单位", "换算", "量纲"],
    "概念不清": ["概念", "理解", "不清", "混淆概念"],
    "计算失误": ["计算", "算错", "数学"],
}


def detect_blindspots(user_id: str = "default") -> dict:
    """
    从错题本分析用户的薄弱环节。
    
    参数:
        user_id: 用户标识（当前保留，未做多用户分离）
    
    返回:
        dict: {total_errors, by_topic: [...], by_error_type: [...], patterns: [...], suggestions: [...]}
    """
    records = get_error_notebook()
    
    if len(records) < 3:
        return {
            "total_errors": len(records),
            "by_topic": [],
            "by_error_type": [],
            "patterns": ["📊 数据不足，请多做几道题再分析（至少需要3条错题记录）"],
            "suggestions": ["📝 继续做题并记录错题，积累足够数据后将自动生成分析"],
        }
    
    # 按知识点统计
    topic_counter = {}
    for r in records:
        t = r.get("topic", "未分类")
        topic_counter[t] = topic_counter.get(t, 0) + 1
    
    total = len(records)
    by_topic = []
    for t, cnt in sorted(topic_counter.items(), key=lambda x: -x[1]):
        pct = round(cnt / total * 100, 1)
        if pct >= 30:
            assessment = "🔴 薄弱环节严重，需要重点突破"
        elif pct >= 15:
            assessment = "🟡 存在明显不足，建议加强练习"
        elif pct >= 5:
            assessment = "🟢 偶有出错，巩固即可"
        else:
            assessment = "✅ 掌握较好"
        by_topic.append({
            "topic": t,
            "count": cnt,
            "percentage": pct,
            "assessment": assessment,
        })
    
    # 按错误类型统计
    error_type_counter = {}
    for r in records:
        reason = r.get("error_reason", "")
        classified = False
        for etype, keywords in _ERROR_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in reason:
                    error_type_counter[etype] = error_type_counter.get(etype, 0) + 1
                    classified = True
                    break
            if classified:
                break
        if not classified:
            error_type_counter["其他"] = error_type_counter.get("其他", 0) + 1
    
    by_error_type = []
    for et, cnt in sorted(error_type_counter.items(), key=lambda x: -x[1]):
        pct = round(cnt / total * 100, 1)
        by_error_type.append({
            "type": et,
            "count": cnt,
            "percentage": pct,
        })
    
    # 发现模式
    patterns = []
    # 找出最薄弱的知识点
    weakest_topic = by_topic[0] if by_topic else None
    if weakest_topic and weakest_topic["percentage"] >= 20:
        patterns.append(f"📌 你在「{weakest_topic['topic']}」上出错最多（占{weakest_topic['percentage']}%），这是你的核心薄弱点")
    
    # 找出最常见的错误类型
    weakest_type = by_error_type[0] if by_error_type else None
    if weakest_type and weakest_type["percentage"] >= 25:
        patterns.append(f"📌 你最常犯的错误类型是「{weakest_type['type']}」（占{weakest_type['percentage']}%）")
    
    # 检查错误类型的组合模式
    if any(et["type"] == "概念不清" for et in by_error_type) and any(et["type"] == "公式记错" for et in by_error_type):
        patterns.append("📌 你同时存在「概念不清」和「公式记错」的问题，建议先理解物理概念再记忆公式")
    
    if any(et["type"] == "计算失误" for et in by_error_type) and any(et["type"] == "符号/方向" for et in by_error_type):
        patterns.append("📌 你的「计算失误」和「符号/方向」问题同时出现，建议解题时放慢速度，分步检查")
    
    # 给建议
    suggestions = []
    
    # 基于薄弱知识点的建议
    if weakest_topic:
        kp = PHYSICS_KNOWLEDGE.get(weakest_topic["topic"])
        if kp:
            formulas = kp.get("formulas", [])
            suggestions.append(
                f"📖 针对「{weakest_topic['topic']}」的复习建议：\n"
                f"  • 仔细阅读基础概念：{kp['basic'][:80]}...\n"
                f"  • 熟记关键公式：{'；'.join(formulas)}\n"
                f"  • 多做此类题型的变式练习"
            )
    
    # 基于错误类型的建议
    for et in by_error_type:
        if et["type"] == "公式记错" and et["percentage"] >= 15:
            suggestions.append(f"📝 公式记忆技巧：建立公式推导树，从基本原理推导公式而不死记硬背")
        elif et["type"] == "符号/方向" and et["percentage"] >= 15:
            suggestions.append(f"📝 符号问题：解题时先规定正方向，每一步检查符号是否与规定方向一致")
        elif et["type"] == "单位换算" and et["percentage"] >= 10:
            suggestions.append(f"📝 单位换算：建议牢记SI基本单位，每次计算前先将所有物理量转换为SI单位")
        elif et["type"] == "概念不清" and et["percentage"] >= 15:
            suggestions.append(f"📝 概念理解：尝试用费曼学习法——用自己的话把概念讲给一个完全不懂的人听")
        elif et["type"] == "计算失误" and et["percentage"] >= 15:
            suggestions.append(f"📝 计算准确度：建议分步计算，每步检查物理量的单位和数量级是否合理")
    
    if not suggestions:
        suggestions.append("👍 总体掌握良好，继续保持！")
    
    if not patterns:
        patterns.append("📊 已分析你的错题模式，暂未发现显著规律。建议积累更多错题后再次分析。")
    
    return {
        "total_errors": total,
        "by_topic": by_topic,
        "by_error_type": by_error_type,
        "patterns": patterns,
        "suggestions": suggestions,
    }


# ══════════════════════════════════════════════════════════════════
# 功能5：手写笔记→知识图谱 (Note to Knowledge Graph)
# ══════════════════════════════════════════════════════════════════

# 物理术语映射：从常见用语到知识点名称
_PHYSICS_TERM_MAP = {
    "牛顿": "牛顿运动定律",
    "惯性": "牛顿运动定律",
    "牛顿定律": "牛顿运动定律",
    "受力": "受力分析",
    "摩擦力": "受力分析",
    "弹力": "受力分析",
    "重力": "受力分析",
    "动量": "动量守恒",
    "冲量": "动量守恒",
    "碰撞": "动量守恒",
    "反冲": "动量守恒",
    "功": "功与能",
    "动能": "功与能",
    "势能": "功与能",
    "机械能": "功与能",
    "能量守恒": "功与能",
    "圆周运动": "圆周运动与万有引力",
    "万有引力": "圆周运动与万有引力",
    "向心力": "圆周运动与万有引力",
    "向心加速度": "圆周运动与万有引力",
    "卫星": "圆周运动与万有引力",
    "开普勒": "圆周运动与万有引力",
    "简谐": "简谐振动",
    "弹簧振子": "简谐振动",
    "单摆": "简谐振动",
    "阻尼": "简谐振动",
    "共振": "简谐振动",
    "波": "波动",
    "振动": "波动",
    "机械波": "波动",
    "干涉": "波动",
    "多普勒": "波动",
    "电场": "库仑定律与电场",
    "库仑": "库仑定律与电场",
    "点电荷": "库仑定律与电场",
    "高斯定理": "高斯定理",
    "电通量": "高斯定理",
    "电势": "电势与电势差",
    "电压": "电势与电势差",
    "等势": "电势与电势差",
    "电容": "电容与电容器",
    "电容器": "电容与电容器",
    "静电屏蔽": "静电场中的导体",
    "尖端放电": "静电场中的导体",
    "导体": "静电场中的导体",
    "法拉第笼": "静电场中的导体",
    "磁场": "恒磁场与毕奥-萨伐尔定律",
    "毕奥": "恒磁场与毕奥-萨伐尔定律",
    "萨伐尔": "恒磁场与毕奥-萨伐尔定律",
    "磁感应": "恒磁场与毕奥-萨伐尔定律",
    "洛伦兹力": "恒磁场与毕奥-萨伐尔定律",
    "安培环路": "安培环路定理",
    "电磁感应": "电磁感应",
    "感应电动势": "电磁感应",
    "法拉第": "电磁感应",
    "楞次": "电磁感应",
    "自感": "电磁感应",
    "互感": "电磁感应",
    "麦克斯韦": "麦克斯韦方程组",
    "电磁波": "电磁波",
    "坡印廷": "电磁波",
    "光速": "电磁波",
    "干涉": "光的干涉",
    "双缝": "光的干涉",
    "薄膜": "光的干涉",
    "牛顿环": "光的干涉",
    "衍射": "光的衍射",
    "光栅": "光的衍射",
    "布拉格": "光的衍射",
    "热力学": "热力学第零一定律",
    "内能": "热力学第零一定律",
    "焓": "热力学第零一定律",
    "热容": "热力学第零一定律",
    "熵": "热力学第二定律",
    "卡诺": "热力学第二定律",
    "热机": "热力学第二定律",
    "制冷": "热力学第二定律",
    "理想气体": "理想气体",
    "状态方程": "理想气体",
    "压强": "理想气体",
    "黑体": "黑体辐射与普朗克量子假设",
    "普朗克": "黑体辐射与普朗克量子假设",
    "光电": "光电效应",
    "光子": "光电效应",
    "逸出功": "光电效应",
    "德布罗意": "波粒二象性与德布罗意波",
    "不确定": "不确定原理",
    "海森堡": "不确定原理",
    "薛定谔": "薛定谔方程",
    "波函数": "薛定谔方程",
    "势阱": "薛定谔方程",
    "量子": "薛定谔方程",
    "能级": "原子结构与能级",
    "原子": "原子结构与能级",
    "玻尔": "原子结构与能级",
    "光谱": "原子结构与能级",
    "量子数": "原子结构与能级",
    "泡利": "原子结构与能级",
    "能带": "能带理论与半导体",
    "禁带": "能带理论与半导体",
    "半导体": "能带理论与半导体",
    "费米": "能带理论与半导体",
    "PN结": "PN结",
    "二极管": "PN结",
    "整流": "PN结",
    "太阳能": "PN结",
    "载流子": "载流子输运",
    "迁移率": "载流子输运",
    "霍尔": "载流子输运",
}


def extract_physics_terms(text: str) -> list:
    """
    从文本中提取物理术语。
    
    参数:
        text: 用户输入的文本
    
    返回:
        list: 匹配到的知识点名称列表
    """
    if not text:
        return []
    
    matched_terms = set()
    
    # 方法1：直接匹配知识点名称
    for key in PHYSICS_KNOWLEDGE:
        if key[:2] in text or key in text:
            matched_terms.add(key)
    
    # 方法2：通过术语映射匹配
    for term, knowledge_key in _PHYSICS_TERM_MAP.items():
        if term in text:
            matched_terms.add(knowledge_key)
    
    return sorted(list(matched_terms))


def generate_knowledge_graph(terms: list) -> dict:
    """
    根据提取的物理术语生成知识图谱。
    
    参数:
        terms: 知识点名称列表
    
    返回:
        dict: {nodes: [{id, name, subject, exam_probability}], edges: [{source, target, relation}]}
    """
    if not terms:
        return {
            "nodes": [],
            "edges": [],
            "warning": "⚠️ 未从文本中识别出物理知识点。请尝试输入更具体的物理术语，如「牛顿定律」「电磁感应」「量子」等。",
        }
    
    # 节点
    node_id_map = {}
    nodes = []
    for i, term in enumerate(terms):
        kp = PHYSICS_KNOWLEDGE.get(term, {})
        node_id = f"n{i}"
        node_id_map[term] = node_id
        nodes.append({
            "id": node_id,
            "name": term,
            "subject": kp.get("subject", ""),
            "exam_probability": kp.get("exam_probability", 0),
        })
    
    # 边：基于知识点之间的 related 关系
    edges = []
    seen_edges = set()
    for term in terms:
        kp = PHYSICS_KNOWLEDGE.get(term, {})
        related = kp.get("related", [])
        for rel in related:
            if rel in node_id_map:
                source = node_id_map[term]
                target = node_id_map[rel]
                edge_key = f"{source}-{target}"
                rev_edge_key = f"{target}-{source}"
                if edge_key not in seen_edges and rev_edge_key not in seen_edges:
                    edges.append({
                        "source": source,
                        "target": target,
                        "relation": "关联",
                    })
                    seen_edges.add(edge_key)
    
    # 如果节点间没有 related 边，但节点数>=2，自动添加顺序边
    if not edges and len(nodes) >= 2:
        for i in range(len(nodes) - 1):
            edges.append({
                "source": nodes[i]["id"],
                "target": nodes[i + 1]["id"],
                "relation": "相邻知识点",
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
    }


# ══════════════════════════════════════════════════════════════════
# 功能6：实验设计训练 (Experiment Trainer)
# ══════════════════════════════════════════════════════════════════

# 实验设备清单
_EXPERIMENT_EQUIPMENT = {
    "力学": [
        "气垫导轨", "滑块", "光电门", "数字计时器", "弹簧", "砝码组",
        "斜面轨道", "打点计时器", "纸带", "天平", "测力计",
        "单摆装置", "秒表", "米尺", "游标卡尺",
    ],
    "电磁学": [
        "直流电源", "电压表", "电流表", "电阻箱", "滑线变阻器",
        "电容器组", "电感线圈", "示波器", "信号发生器",
        "霍尔元件", "螺线管", "磁铁", "检流计", "万用表",
    ],
    "热学": [
        "温度计", "量热器", "气压计", "烧杯", "酒精灯",
        "恒温水浴", "压强传感器", "体积计",
    ],
    "波动光学": [
        "激光器", "双缝", "单缝", "光栅", "凸透镜",
        "偏振片", "白屏", "米尺", "分光计", "钠光灯",
    ],
    "量子物理": [
        "光电管", "微电流放大器", "单色仪", "汞灯", "滤光片",
        "光功率计", "数字电压表", "电位差计",
    ],
    "半导体物理": [
        "半导体特性测试仪", "恒温箱", "探针台", "万用表",
        "示波器", "直流电源", "变阻器",
    ],
}


def generate_experiment_question(topic: str = "") -> dict:
    """
    生成实验设计题。
    
    参数:
        topic: 知识点（空=随机选题）
    
    返回:
        dict: {title, equipment, scenario, question, expected_approach, followups}
    """
    # 选题
    if topic:
        kp = PHYSICS_KNOWLEDGE.get(topic)
        if not kp:
            return {"error": f"❌ 未找到知识点「{topic}」"}
        subject = kp.get("subject", "")
    else:
        # 随机选题
        keys = list(PHYSICS_KNOWLEDGE.keys())
        topic = random.choice(keys)
        kp = PHYSICS_KNOWLEDGE[topic]
        subject = kp.get("subject", "")
    
    # 从设备库中获取该科目的设备
    equipment = _EXPERIMENT_EQUIPMENT.get(subject, _EXPERIMENT_EQUIPMENT.get("力学", []))
    # 随机选 4-7 个设备
    selected_equip = random.sample(equipment, min(random.randint(4, 7), len(equipment)))
    
    # 生成情景描述
    scenarios = {
        "力学/牛顿运动定律": "在物理实验室中，你需要设计一个实验来验证牛顿第二定律 F=ma。",
        "力学/动量守恒": "使用气垫导轨设计实验验证动量守恒定律。",
        "力学/简谐振动": "请你设计实验测量弹簧振子的振动周期，并验证周期公式 T=2π√(m/k)。",
        "电磁学/库仑定律与电场": "设计实验验证库仑定律，测量两个点电荷之间的静电力。",
        "电磁学/电磁感应": "设计一个实验来演示法拉第电磁感应定律，并探究影响感应电动势的因素。",
        "电磁学/霍尔效应": "利用霍尔元件设计实验测量未知磁场的磁感应强度。",
        "波动光学/光的干涉": "利用双缝干涉测量光的波长。",
        "波动光学/光的衍射": "利用单缝衍射现象测量缝宽。",
        "热学/理想气体": "设计实验验证理想气体状态方程 PV=nRT。",
        "量子物理/光电效应": "利用光电效应实验测量普朗克常数。",
        "半导体物理/PN结": "设计实验测量PN结的伏安特性曲线。",
    }
    
    # 查找最匹配的情景
    scenario_text = ""
    for key, desc in scenarios.items():
        if topic in key or subject in key:
            scenario_text = desc
            break
    
    if not scenario_text:
        scenario_text = f"在物理实验室中，你需要设计一个与「{topic}」相关的实验。"
    
    # 生成问题
    question = (
        f"📋 **实验题目**：{topic} 实验设计\n\n"
        f"**情景**：{scenario_text}\n\n"
        f"**可用设备**：{'、'.join(selected_equip)}\n\n"
        f"**设计要求**：\n"
        f"(1) 画出实验装置示意图并说明实验原理\n"
        f"(2) 写出实验步骤\n"
        f"(3) 设计数据记录表格\n"
        f"(4) 说明如何处理数据以验证相关物理规律\n"
        f"(5) 分析可能的误差来源及减小误差的方法"
    )
    
    # 预期方法
    formulas = kp.get("formulas", [])
    advanced = kp.get("advanced", "")
    expected_approach = (
        f"🔬 **预期实验方法**\n\n"
        f"1. **原理**：利用 {formulas[0] if formulas else topic} 这一核心公式，"
        f"通过测量相关物理量来验证或测定参数。\n"
        f"2. **测量方法**：{advanced[:150] if advanced else '采用控制变量法，多次测量取平均值'}\n"
        f"3. **数据处理**：列表法记录数据，作图法（如拟合直线）得到相关参数\n"
        f"4. **误差分析**：系统误差（仪器精度、环境因素）和偶然误差（读数误差）"
    )
    
    # 追问列表
    followups = [
        "如果给定的设备有限（只有基础工具），你会如何简化实验设计？",
        "这个实验在工程实践中有哪些实际应用？",
        "如果要在太空（微重力环境）做这个实验，需要做哪些调整？",
        "实验结果的误差主要来自哪些方面？如何定量评估？",
        "能否用另一套完全不同的实验方法验证同一个物理规律？",
    ]
    
    # 根据知识点选择2-3个合适的追问
    selected_followups = random.sample(followups, min(3, len(followups)))
    selected_followups.insert(0, f"在你的实验方案中，如何确保「{topic}」相关的关键物理量测量准确？")
    
    return {
        "title": f"🧪 实验设计训练 · {topic}",
        "equipment": selected_equip,
        "scenario": scenario_text,
        "question": question,
        "expected_approach": expected_approach,
        "followups": selected_followups,
    }


# ══════════════════════════════════════════════════════════════════
# 功能7：碎片时间卡片 (Quick Cards)
# ══════════════════════════════════════════════════════════════════

def generate_quick_cards(subject: str = "", count: int = 5) -> list:
    """
    生成碎片时间快速自测卡片。
    
    参数:
        subject: 科目筛选（空=全部科目）
        count: 卡片数量（默认5张）
    
    返回:
        list[dict]: 每张卡片 {id, topic, question, options, answer, explanation, difficulty}
    """
    # 收集候选知识点
    candidates = []
    for name, kp in PHYSICS_KNOWLEDGE.items():
        if subject and kp.get("subject", "") != subject:
            continue
        candidates.append((name, kp))
    
    if not candidates:
        return [{"error": f"❌ 未找到科目「{subject}」的知识点"}]
    
    # 随机选择 count 个知识点
    selected = random.sample(candidates, min(count, len(candidates)))
    
    cards = []
    for i, (name, kp) in enumerate(selected):
        card_id = f"card_{int(_time.time() * 1000)}_{i}"
        subject_name = kp.get("subject", "")
        difficulty = kp.get("exam_probability", 3)
        formulas = kp.get("formulas", [])
        basic = kp.get("basic", "")
        
        # 掷骰子决定是选择题还是填空题
        is_choice = random.random() < 0.6  # 60% 概率出选择题
        
        if is_choice:
            # 选择题：4个选项
            f_str = formulas[0] if formulas else ""
            
            # 生成不同题型的题目
            choice_type = random.choice(["formula", "concept", "application", "unit"])
            
            if choice_type == "formula" and f_str:
                # 公式题：哪个公式正确
                question = f"关于「{name}」，以下哪个公式/表述是正确的？"
                correct_choice = f_str
                # 生成干扰项
                distractors = set()
                # 从其他知识点中偷公式作为干扰项
                other_formulas = []
                for oname, okp in PHYSICS_KNOWLEDGE.items():
                    if oname != name:
                        other_formulas.extend(okp.get("formulas", []))
                random.shuffle(other_formulas)
                
                distractors_list = []
                for of in other_formulas:
                    if of != correct_choice and of not in distractors:
                        distractors.add(of)
                        distractors_list.append(of)
                    if len(distractors_list) >= 3:
                        break
                
                # 如果干扰项不够，补充文字干扰项
                if len(distractors_list) < 3:
                    fallbacks = ["F = -kx（适用于任何情况）", "E = mc²", "PV = constant（所有过程）", "F = qvB（速度任意方向）"]
                    for fb in fallbacks:
                        if fb != correct_choice and fb not in distractors:
                            distractors.add(fb)
                            distractors_list.append(fb)
                        if len(distractors_list) >= 3:
                            break
                
                options_list = [correct_choice] + distractors_list[:3]
                random.shuffle(options_list)
                
                answer_letter = chr(65 + options_list.index(correct_choice))
                answer = f"{answer_letter}. {correct_choice}"
                explanation = f"这是「{name}」的核心公式。{advanced[:100] if kp.get('advanced') else basic[:100]}"
                
            elif choice_type == "concept":
                question = f"关于「{name}」，以下哪个说法是正确的？"
                # 从 basic 中提取关键陈述作为正确答案
                sentences = [s.strip() for s in basic.split("。") if s.strip()]
                correct_stmt = sentences[0] if sentences else f"{name}是物理学中的重要概念。"
                if len(correct_stmt) > 60:
                    correct_stmt = correct_stmt[:57] + "..."
                
                distractors_list = [
                    f"{name}与牛顿运动定律无关",
                    f"{name}只在真空中成立",
                    f"{name}已经被现代物理完全否定",
                ]
                
                options_list = [correct_stmt] + distractors_list
                random.shuffle(options_list)
                
                answer_letter = chr(65 + options_list.index(correct_stmt))
                answer = f"{answer_letter}. {correct_stmt}"
                explanation = f"{basic[:150]}"
                
            else:  # application or unit
                question = f"以下哪项不是「{name}」的实际应用？"
                apps = kp.get("applications", {})
                all_apps = []
                for k in ["daily", "engineering", "research"]:
                    v = apps.get(k, "")
                    if v:
                        all_apps.extend([s.strip() for s in v.split("；") if s.strip()])
                
                if len(all_apps) >= 4:
                    correct_app = all_apps[0]
                    fake_apps = [
                        "利用磁悬浮实现星际旅行",
                        "用冷冻法测量光速",
                        "用弹簧秤称量电荷量",
                        "在真空中用扩音器传播声音",
                        "用于制造永动机",
                        "作为常温超导材料",
                    ]
                    distractors_list = random.sample(fake_apps, 3)
                    options_list = [correct_app] + distractors_list
                    random.shuffle(options_list)
                    answer_letter = chr(65 + options_list.index(correct_app))
                    answer = f"{answer_letter}. {correct_app}"
                    explanation = f"{correct_app} 确实是 {name} 的应用之一，其余选项均不为该知识点的实际应用。"
                else:
                    # 退化为公式题
                    question = f"以下哪个公式与「{name}」相关？"
                    correct_choice = formulas[0] if formulas else f"{name}的核心概念"
                    distractors_list = ["E = mc²", "F = -kx", "PV = nRT"]
                    options_list = [correct_choice] + distractors_list
                    random.shuffle(options_list)
                    answer_letter = chr(65 + options_list.index(correct_choice))
                    answer = f"{answer_letter}. {correct_choice}"
                    explanation = f"这是{name}的基本公式之一。"
            
            card = {
                "id": card_id,
                "topic": name,
                "subject": subject_name,
                "question": question,
                "options": options_list,
                "answer": answer,
                "explanation": explanation,
                "difficulty": difficulty,
                "type": "choice",
            }
        else:
            # 填空题
            f_str = formulas[0] if formulas else ""
            if f_str:
                # 挖空公式
                parts = f_str.split("=")
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    if len(right) > 5:
                        # 挖空右边部分
                        question = f"「{name}」的核心公式是 {left} = ______（请填写完整表达式）"
                        answer = right
                        explanation = f"{left} = {right} 是 {name} 的基本公式。{basic[:100]}"
                    else:
                        question = f"「{name}」的核心公式是 ______ = {right}（请填写完整表达式）"
                        answer = left
                        explanation = f"{left} = {right} 是 {name} 的基本公式。{basic[:100]}"
                else:
                    question = f"请写出「{name}」的一个关键公式："
                    answer = f_str
                    explanation = f"{basic[:150]}"
            else:
                question = f"请简述「{name}」的核心概念："
                key_sentences = [s.strip() for s in basic.split("。") if s.strip()]
                answer = key_sentences[0] if key_sentences else f"{name}是物理学的重要基础概念。"
                explanation = f"{basic[:150]}"
            
            card = {
                "id": card_id,
                "topic": name,
                "subject": subject_name,
                "question": question,
                "options": None,
                "answer": answer,
                "explanation": explanation,
                "difficulty": difficulty,
                "type": "fill",
            }
        
        cards.append(card)
    
    return cards


# ══════════════════════════════════════════════════════════════════
# 综合功能菜单
# ══════════════════════════════════════════════════════════════════

def get_all_innovation_menus() -> str:
    """
    返回所有创新功能的中文菜单说明。
    
    返回:
        str: 格式化后的功能菜单
    """
    menu = """
╔══════════════════════════════════════════════════════╗
║        🚀 Smart Tutor · 创新功能菜单              ║
╚══════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 **功能1：一题通全章**
  生成一道贯穿整个章节的综合题，从基础到进阶逐步深入。
  一个知识点接着一个知识点，做完一题 = 复习一章！
  └ 命令：`chain_question("电磁学")` → 查看更多科目链

🎮 **功能2：Boss战模式**
  游戏化闯关系统！先打小怪积累经验，最后挑战大Boss！
  └ 三步走：`start_boss_session("力学")`
           → `fight_miniboss(session_id, mb_id)`
           → `fight_boss(session_id)`
  └ 查进度：`get_boss_progress(session_id)`

🎯 **功能3：考试热点预测**
  基于知识库统计，预测高频考点，科学分配复习时间！
  └ 命令：`predict_exam_topics("电磁学", 10)`
  └ 不填科目：`predict_exam_topics()` 全部科目

🔍 **功能4：物理盲点探测器**
  从你的错题本中智能分析薄弱环节，给出针对性建议！
  └ 命令：`detect_blindspots()`
  └ 需要至少3条错题记录才能分析

📊 **功能5：笔记→知识图谱**
  把你的学习笔记中的物理关键词提取出来，生成知识图谱！
  └ 两步走：`terms = extract_physics_terms("你的笔记文本")`
           → `generate_knowledge_graph(terms)`

🧪 **功能6：实验设计训练**
  基于真实物理实验，训练实验设计能力！
  └ 命令：`generate_experiment_question("电磁感应")`
  └ 随机出题：`generate_experiment_question()`

📇 **功能7：碎片时间卡片**
  快速自测卡片（选择题/填空题），利用碎片时间巩固知识！
  └ 命令：`generate_quick_cards("量子物理", 5)`
  └ 随机出题：`generate_quick_cards()`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **快速开始**：在 Python 中导入 physics_kb：
    >>> from physics_kb import *
    >>> get_all_innovation_menus()
"""
    return menu
