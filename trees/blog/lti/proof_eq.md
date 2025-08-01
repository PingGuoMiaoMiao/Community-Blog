---
title: Proof Sketch
collect: true
---

至此，我们已经完整地定义了一个由「变量消去」、「约束生成」和「参数计算」三步构成的、完全可执行的算法。但我们如何确保这个具体的算法，其行为与那个非构造性的、声明式的 `App-InfSpec` 规约完全一致？

其等价性的证明，浓缩于一个核心命题中，该命题断言：

1. **若最小代换 $\sigma_{CR}$ 存在，那么它就是规约所要求的那个最优解。**
2. **若最小代换 $\sigma_{CR}$ 不存在，那么规约所要求的最优解也必然不存在。**

**证明概要：**

- **第一部分（算法的正确性）**：
  为证明 $\sigma_{CR}$ 是最优的，我们任取另一个满足约束的合法代换 $\sigma'$，并需要证明 $\sigma_{CR}(R) \lt: \sigma'(R)$。
  考虑构建一个从 $\sigma_{CR}$ 到 $\sigma'$ 的「代换链」，每一步只改变一个变量的值。例如，$\sigma_0 = \sigma_{CR}$，$\sigma_1 = \sigma_0[X_1 \mapsto \sigma'(X_1)]$，...，$\sigma_n = \sigma'$。
  接着，我们证明在此路径的每一步中，结果类型都是单调不减的，即 $\sigma_{i-1}(R) \lt: \sigma_i(R)$。这一步的证明，直接依赖于前述的极性定义。例如，若 $R$ 在 $X_i$ 上是协变的，我们的算法选择了下界 $S$，而 $\sigma'(X_i)$ 必然大于等于 $S$，因此根据协变的定义，结果类型必然「变大」。同理可以证明其他情况下该论断也成立。
  最终，通过传递性，我们得出 $\sigma_{CR}(R) \lt: \sigma'(R)$，证明了 $\sigma_{CR}$ 的最优性。

- **第二部分（算法失败的完备性）**：
  当算法失败时，必然是因为某个不变变量 $X_i$ 的约束区间 $[S, T]$ 中 $S \neq T$。
  我们采用反证法：假设此时仍然存在一个最优解 $\sigma$。由于 $S \neq T$，我们总能找到另一个合法的代换 $\sigma'$，使得 $\sigma(X_i)$ 与 $\sigma'(X_i)$ 不同。但由于 $R$ 在 $X_i$ 上是不变的，$\sigma(R)$ 与 $\sigma'(R)$ 将变得不可比较，这与「$\sigma$ 是最优解（即比所有其他解都小）」的假设相矛盾。
  因此，在这种情况下，最优解必然不存在。