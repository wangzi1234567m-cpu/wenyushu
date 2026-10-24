# safety

唯一 Owner 的表定义位于本模块 infrastructure。跨模块只使用 application 公开端口。
P0 只实现 identity 基础链路；其余业务在所属阶段实现，不提供占位成功接口。
