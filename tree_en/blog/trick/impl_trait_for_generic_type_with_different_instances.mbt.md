
```markdown
---
title: Implementing Trait for Different Instances of Generic Types
collect: true
author: [illusory0x0](https://github.com/illusory0x0)
taxon: Blog
date: 2025-08-29
---

# Implementing Trait for Different Instances of Generic Types

## Problem Background

In MoonBit, directly implementing the same trait for different concrete instances of a generic type will cause a compilation error.

For example, the following code triggers a compiler error:
```
The method Show::output for type Hex has been defined
```

```mbt skip  
struct Hex[T](T)

impl Show for Hex[Int] with output(self, logger) {
  // Hexadecimal output implementation for Int
}

impl Show for Hex[UInt] with output(self, logger) {
  // Hexadecimal output implementation for UInt
}
```

This occurs because the compiler considers it a redefinition of the `Show::output` method for type `Hex`, even though the type parameters differ.

## Solution

We can bypass the compiler's limitation by defining a dedicated `HexShow` trait and leveraging default implementations along with specialized implementations.

### Core Idea

Instead of directly implementing the trait for `Hex[T]`, we implement the corresponding trait for the type parameter `T`, thereby indirectly achieving the desired functionality.

### Implementation Code

```mbt
trait HexShow: Show {
  output(Self, &Logger) -> Unit = _
}

struct Hex[T](T)

impl[T : HexShow] Show for Hex[T] with output(self, logger) {
  HexShow::output(self.inner(), logger)
}

/// Default implementation: uses standard Show output
impl HexShow with output(self, logger) {
  Show::output(self, logger)
}

/// Specialized implementation for Int: outputs hexadecimal format
impl HexShow for Int with output(self, logger) {
  logger.write_string(self.to_string(radix=16))
}

/// Specialized implementation for UInt: outputs hexadecimal format
impl HexShow for UInt with output(self, logger) {
  logger.write_string(self.to_string(radix=16))
}

test {
  let a = -0xaabb
  let b = 0xaabb
  inspect(Hex(a), content="-aabb")
  inspect(Hex(b), content="aabb")
}
```

### How It Works

1. **Define auxiliary trait**: `HexShow` inherits from `Show` and provides a default implementation marker `= _`
2. **Generic constraint**: The `Show` implementation for `Hex[T]` requires `T` to implement `HexShow`
3. **Delegate call**: The output method of `Hex[T]` delegates to `HexShow::output` of the inner value
4. **Type specialization**: Provide specialized `HexShow` implementations for different concrete types (e.g., `Int`, `UInt`)

## Comparison with Other Languages

This approach differs from Haskell's [FlexibleInstances](https://ghc.gitlab.haskell.org/ghc/doc/users_guide/exts/instances.html#extension-FlexibleInstances) extension, as MoonBit's workaround imposes stricter limitations on flexibility.

*Acknowledgements to [myfreess](https://github.com/myfreess) for highlighting this important distinction.*

## Applicable Scenarios

This pattern is suitable when:
- Different behavior implementations are needed for different instances of a generic type
- Type safety must be maintained while avoiding code duplication
- Type specialization at compile time is required
```