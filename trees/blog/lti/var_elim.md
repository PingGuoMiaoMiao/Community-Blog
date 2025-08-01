---
title: Variable Elimination
collect: true
---

设想我们想为变量 $X$ 生成约束，以使得类型 $\forall Y. () \to (Y\to Y)$ 成为 $\forall Y. () \to X$ 的一个子类型。根据函数子类型的逆变/协变规则，这要求 $Y \to Y \lt: X$。然而，我们不能直接生成约束 $\{ Y \to Y \lt: X \lt: \top\}$，因为类型变量 $Y$ 在此约束中是自由的，但它本应被 $\forall Y$ 所绑定，这就造成了一种作用域错误。

正确的做法是，找到 $Y \to Y$ 的一个不含 $Y$ 的、且尽可能精确的超类型，并用它来约束 $X$。在本例中，即 $\bot \to \top$。变量消去机制，正是为了形式化地完成这一「寻找最精确边界」的任务。

1. 提升 (Promotion), $S \Uparrow^V T$：$T$ 是 $S$ 的一个不含集合 $V$ 中任何自由变量的**最小超类型**。
2. 下降 (Demotion), $S \Downarrow^V T$：$T$ 是 $S$ 的一个不含集合 $V$ 中任何自由变量的**最大子类型**。

这两套关系由一组递归的定则所定义，确保了对于任何类型 $S$ 和变量集 $V$，其结果 $T$ 都是唯一且总能被计算出来的（即它们是全函数）。
此处建议读者停下来思考一下，如何设计这两套关系的递归规则并自己使用代码实现它（提示：对于提升规则的情况，若 $X\in V$ 则将其提升到 $\top$，反之不变，其他情况是显然的）

[+-](/blog/lti/ve_rules.md#:embed)

这套精心设计的规则，保证了变量消去操作的正确性与最优性，这由两个关键引理所保证：

- **可靠性（Soundness）**：若 $S \Uparrow^V T$，那么可以证明 $S \lt: T$ 且 $T$ 中确实不含 $V$ 中的自由变量。对偶地，若 $S \Downarrow^V T$，则 $T \lt: S$ 且 $T$ 不含 $V$ 中的自由变量。
- **完备性（Completeness）**：此操作找到了「最好」的边界。例如，对于提升操作，若存在另一个不含 $V$ 中变量的 $S$ 的超类型 $T'$，那么 $S \Uparrow^V T$ 所计算出的 $T$ 必然是 $T'$ 的子类型（即 $T \lt: T'$），这证明了 $T$ 是所有可能选项中最小的那一个。
