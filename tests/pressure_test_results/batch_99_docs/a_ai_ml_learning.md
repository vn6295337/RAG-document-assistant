oo================================================================================
  PHASE I – MATHEMATICAL FOUNDATIONS
  ================================================================================

  LINEAR ALGEBRA
- [ ]Vectors and matrices
    - [x] Vector operations (addition, scalar multiplication, dot product)
        - [ ]Vector addition is just combining two “ingredient lists” entry by entry. You happen to see it in real life whenever you stack contributions from different sources. Friend A's is [4, 6, 2]; friend B’s is [3, 2, 5]. Adding the vectors gives [7, 8, 7], the total hours watched by both in each category.
        - [ ]scalar multiplication simply scales the whole “recipe” up or down. The proportions stay identical; you’re just changing how much of everything you have
        - [ ]The vector dot product takes two equal-length lists of numbers, multiplies each matching pair, and sums the results—yielding a single number that reflects how strongly the two vectors align. The dot product is only defined when both vectors have the same number of components—each entry in one vector must pair with exactly one entry in the other

    - [x] Matrix operations (multiplication, transpose)
        - [x] Matrix multiplication generalizes the vector dot product. 
            -Matrix B (3 × 2) tells how much of each ingredient (columns: apples, bananas) goes into two intermediate juice bases (rows):

          $$
          B = \begin{bmatrix}
                3 & 1 \\
                2 & 2 \\
                1 & 4
          \end{bmatrix}
          $$

          -Matrix A (2 × 3) says how to mix those bases into final drinks (rows = drinks, columns = bases):

          $$
          A = \begin{bmatrix}
                2 & 0 & 1 \\
                1 & 1 & 1
          \end{bmatrix}
          $$

          -When you compute $A \times B$, each entry is a row–column dot product. For Drink X and ingredient “apples” it is $2\cdot3 + 0\cdot2 + 1\cdot1 = 7$, meaning Drink X ultimately needs 7 apples.
          -When computing matrix products, operations flow from left to right. This is just a convention, not a mathematical requirement.
              A . B . C : A acts on B, and then the result acts on C. This is the convention for any side of an equation. 
              Associative property, A. B . C = (A . B) . C = A . (B . C). Both give the same answer. But not commutative, A . B ≠ B . A
         -When applying transformation to vectors, operations flow from right to left. This is not a convention, but forced by mathematical requirement.
             A . B . C . v : First, C.v = y , then B.y = z, and then A.z = result
             Associativity allows us to group operations different ways for computation but function composition dictates that when we apply these matrices to a vector, the right most matrix must operate first - (f . g)(x) = f (g (x))
             A . B . C . v = A . (B . (C . v)) = ((A . B) . C) . v
        - [x] Matrix transpose
          Taking a transpose keeps every number the same; it simply swaps rows with columns.
          When a matrix represents a pure rotation (orthogonal matrix), that swap immediately reverses the rotation, undoing the way the original matrix tilted the axes apart.
          
- - [x] Identity matrix
  The identity matrix is the “do-nothing” transform: multiplying by it leaves every vector unchanged, so it’s the safe baseline when a system might toggle an effect on or off.
  Example: when initializing a neural network layer, random weights can explode or vanish gradients, and zero weights erase the signal entirely. Starting from the identity lets the layer pass inputs straight through, then training only nudges the weights away from that neutral behavior when it actually helps.
- - [x] Zero matrix
  Every entry is zero, so multiplying by it wipes out any input.
  Acts as a “no effect” placeholder; great for marking no connection between features.
  In neural nets, a zero weight matrix shuts a layer off—handy for diagnostics, terrible for initialization. Useful for understanding what each weight contributes—zeroing a layer shows how much downstream behavior depends on it
- - [x] Matrix calculus (Jacobian, Hessian)
    - [x] Derivative of scalar function w.r.t. vectors
        -It is the rate of change of one scalar output per unit change (gradient) in each input
    - [x] Jacobian matrix for vector-valued functions
        -Similar to derivative of scalar function w.r.t. vectors, but for multiple outputs
    - [x] Hessian matrix for second-order derivatives
        -It describes how output's rate of change changes (curvature) per unit change in each input. If there are multiple outputs, there is one Hessian matrix for each output function   
- - [x] Determinant, Trace, Eigenvectors, Eigenvalues
    -**Determinant** of a matrix is the scale factor for 2d, volume factor for 3d, and hypervolume factor for higher dimensions. Essentially, how much the transformation shrinks or stretches the space.
    -**Trace** of a matrix is the sum of its diagonal elements, and it measures total or average behavior of matrix across dimensions. Trace works for only on square matrices. Frobenius norm is used to calculate magnitude of non-square matrices, square root of sum of all squares of matrix elements
    -**Eigenvector** is that vector that is resistant to rotation or deformation by a matrix, it allows only flipping direction and scaling (shrinking or expanding). The matrix determines which vectors are Eigenvectors and what their eigenvalues are.
    -**Eigenvalue** is the scaling factor of eigenvector i.e. how much the vector shrinks or expands. 
    - [x] Computing determinants (cofactor expansion, properties)
        -cofactor expansion is a method to compute determinant of a large matrix (3x3 matrix and beyond) by breaking it down into smaller ones
    - [x] Relationship between trace, determinant, and eigenvalues
        -trace = sum of eigenvalues
        -determinant = product of eigenvalues
- - [x] Matrix inverse
    -It is the undo button or reverse gear for matrix transformations.
    - [x] Conditions for invertibility (det ≠ 0)
        -Not all matrices have an inverse. If det = 0, then the matrix transformation collapses to a lower dimension and it cannot be inverted.
    - [x] Computing inverses (2×2 formula, larger matrices)
        -A matrix's inverse is computed by dividing each element of its adjugate by its determinant.
        -  For a 2×2 matrix [a  b; c  d]
        - Adjugate: Swap the diagonal elements and negate the off-diagonal elements →        [d  -b; -c  a]
        - Determinant: The product of diagonal elements minus the product of off-diagonal elements → ad - bc
        - Gaussian Elimination - Another simpler method where we write matrix A as  [ A | I ] , where I is the identity matrix and use row operations to turn the left side to  I and what becomes of the right is A<sup>-1</sup>   -> [ I |  A<sup>-1</sup> ]
    - [x] Properties of inverses
        1. Property 1: (A⁻¹)⁻¹ = A : Inverse of an inverse gives the original matrix
        2. Property 2: (AB)⁻¹ = B⁻¹A⁻¹ : When you undo two transformations in a sequence, you must undo it in reverse order
        3. Property 3: (A^T)⁻¹ = (A⁻¹)^T : It doesn't matter whether you flip rows and columns of a matrix before or after inverting, the result remains the same
        4. Property 4: det(A⁻¹) = 1/det(A) : If a matrix scales by some amount (det), the inverse scales by the reciprocal of the amount (1/det)
    - [x] Relationship to solving linear systems
        -Write the equations in terms of the coefficient matrix (A), the unknown matrix (X), and the result matrix (Y). Now solve the matrix system using the matrix inverse. A * X = Y  -> X = A<sup>-1</sup> * Y
- - [x] Matrix rank
    - [x] Definition and geometric interpretation
        -Rank is the number of linearly independent rows or columns in a matrix. A row is independent if it cannot be made from other rows. Row rank always equals column rank. Rank tells how much truly independent information exists in a matrix.
        Uses of rank:
          - Detect redundancies in data
          - Check if a system of equations has a solution (compare rank(A) with rank([A|y]))
          - Compress data by removing redundant information
          - Feature engineering in machine learning
          - Understand if a transformation is losing information
          - Detect data quality issues
    - [x] Rank and invertibility
        -Full rank matrices have non-zero determinant (det ≠ 0) and can be inverted. Rank-deficient matrices have rank less than the number of rows (det = 0) and cannot be inverted.
    - [x] Computing rank
        -Perform row operations to simplify the matrix and count non-zero rows. That count is the rank. Row operations do not change the rank.
    - [x] Full rank vs. rank deficient
        -Full rank matrices have all independent rows and produce unique solutions. Rank deficient matrices produce either no solution or infinite solutions.
- - [x] Orthogonal matrices
    -These are the matrices that just rotates/flips a vector without stretching, squishing, or deforming it. The length is preserved. A vector that passing through this matrix that gets only flipped while staying in its same line is the Eigenvector with Eigenvalue -1 (flipping). Orthogonal matrix is typically represented as Q
    - [x] Definition: Q<sup>T</sup> Q = I
        -For an orthogonal matrix Q, the transpose is its inverse: Q<sup>T</sup> Q = I. If Q rotates in one direction, QT rotates in the opposite direction, and together they cancel out to give the identity matrix. A matrix Q is orthogonal if Q<sup>T</sup> Q = I 
    - [x] Preservation of norms and angles
        -Norm (generic name for length) - Rotating a vector doesn't change its 'length' a.k.a. norm. Orthogonal matrix Q applied to any vector v preserves its norm -> ||Qv||<sup>2</sup> = ||v||<sup>2</sup>
            -v = [x₁, x₂, ..., x₁₀₀₀]
            L2 norm = √(x₁² + x₂² + ... + x₁₀₀₀²) - Euclidean norm or geometric length or straight-line length, most common in ML
            L1 norm = |x₁| + |x₂| + ... + |xₙ| - Manhattan norm or city-block distance, used in LASSO regression
            L∞ norm = max(|x₁|, |x₂|, ..., |xₙ|) - Max norm or farthest coordinate, used in robustness analysis
        -Angle - Orthogonal matrix, when rotating vectors, doesn't change the angle between them
    - [x] Rotation and reflection matrices
        -Rotation matrices spin vectors without stretching (det = +1)
        -Reflection matrices mirror-flip vectors (det = -1)
            *Both are orthogonal matrices: they preserve lengths and angles.*
        -When you compose two orthogonal matrices, the result is also orthogonal (Q1 x Q2)<sup>T</sup> x (Q1 x Q2) = I .  This means rotations and reflections can be combined safely without distortion. 
            - In 3D, sequential rotations (Euler angles) can sometimes fail at certain angles (Gimbal Lock). Quertenions are an alternative 4D representation that avoids this problem.
- - [x] Orthogonality and projections
    - [x] Orthogonal vectors
        -Orthogonal vectors are those vectors whose dot product is zero. They are truly independent and don't share information or direction with each other. 
    - [x] Orthonormal sets
        -Orthonormal sets contain vectors that are orthogonal to each other and have unit normalized length. Normalization is calculated by first computing the norm (length) of the vector and then dividing the vector by that norm. Normalization removes the length factor and retains only direction. 
    - [x] Orthogonal projections
        -Orthogonal projection finds the component of a vector in a specific direction. It is used to isoloate specific information from noisy multi-dimensional data. To extract the component v'  of a vector v in the direction of vector u, we use the formula 
            v' = ( v . u )  / ( u . u ) * u
    - [x] Gram-Schmidt process
        -This process converts linearly independent vectors into orthonormal sets. For each vector, compute its orthogonal projection onto all previous vectors, subtract this projection from the vector, and  normalize the result.  This produces an orthonormal set of clean orthogonal vectors with unit length.
        -Key input requirement: The input vectors must be linearly independent .This ensures they can be combined (using linear combinations) to reach ANY point in the space—they form a basis.
        -Why it matters: **Gram-Schmidt** converts messy, correlated real-world data into clean, independent components so we can solve problems efficiently while preserving all information.
    - [x] QR decomposition
        -QR decomposition is a method to break a matrix A into an orthonormal matrix Q and upper triangular matrix R in order to solve linear systems of equation efficiently and stably.
- - [x] Null space & Nullity
    - [x] Null Space: 
        -The set of all input vectors that map to the zero vector when a linear transformation is applied. Vectors in the null space do not affect the output—they can be added to any solution without changing the result.
        -Null space gives you flexibility. Real-world problems rarely have one "perfect" solution. They have infinite solutions that all meet the main goal. Solve Ax = b, then choose the BEST solution from the infinite set using additional criteria.
    - [x] Nullity:
        -The dimension of the null space, i.e., the number of input dimensions that are squished to zero by a matrix transformation. Thus nullity is the number of free direction to move along. If nullity =1, one free direction, infinite line of solutions. If nullity =2, two free directions, infinite plane of solution. and so on.
    - [x] Solutions to Ax = 0
        -This equation identifies all input vectors that, when transformed by matrix A, produce the zero vector. The set of all such solutions forms the null space.
            - Note 1: Inverse problem -> Ax = b. Solve to find input values x that produces the desired output b (harder problem)
            - Note 2: Forward problem -> b = Ax. Matrix multiplication to to find b (computationally easier)
    - [x] Relationship to rank and dimension theorem
        -rank(A) + nullity(A) = number of input dimensions (equal to the number of columns in A)
        -For example, a 3×3 matrix with 2 independent rows (rank = 2) can accept 3D input (indicated by 3 columns), but only 2 of those input dimensions affect the output. Since det(A) = 0, one of the three input dimensions is squished to zero (disappears). Therefore, nullity = 1, and rank + nullity = 2 + 1 = 3.
    - [x] Computing null space basis
        -Using det(A), we determine whether a non-trivial null space exists.
        -Using nullity, we know how many basis vectors are needed to describe the null space.
        -Using null space basis vectors, we know the exact directions where the null space resides, expressed in standard coordinates. Null space provides a slack in the system which is advantageous.
            Real-World Paint Factory Scenario
                Your paint factory has a contract to deliver paint that:
                  -  Is 10 liters total
                  - Has exactly 6 liters of red pigment in it
                    But you have 3 suppliers:
                      - Supplier A: Pure red paint ($10/liter)
                      - Supplier B: Pure blue paint ($5/liter)
                      - Supplier C: Purple paint ($8/liter, pre-mixed 50/50 red-blue)
                      Your constraint: 0 ≤ c ≤ 8
                      Decision Scenarios
                      Scenario 1: Purple paint is cheap that day (c = 8)
                      x₁ = 6 - 0.5(8) = 2 liters red
                      x₂ = 4 - 0.5(8) = 0 liters blue
                      x₃ = 8 liters purple
                      Cost: 2(10) + 0(5) + 8(8) = $84
                      Scenario 2: Red paint is cheap that day (c = 0)
                      x₁ = 6 liters red
                      x₂ = 4 liters blue
                      x₃ = 0 liters purple
                      Cost: 6(10) + 4(5) + 0(8) = $80
                      Scenario 3: Balanced (c = 4)
                      x₁ = 4 liters red
                      x₂ = 2 liters blue
                      x₃ = 4 liters purple
                      Cost: 4(10) + 2(5) + 4(8) = $82
- - [x] Linear transformations
    -We USE linear transformations BECAUSE:
      -Parallel lines staying parallel = structure is preserved
      -Even spacing staying even = proportions are predictable
      -Origin staying fixed = reference points are stable
    -Why this matters practically: Even though physical and biological realities are mostly non- linear,  we can decompose them as: linear portion + non-linear perturbations. Linearity helps us understand the baseline behavior and build intuition, then we layer in non-linear corrections for realistic accuracy.
     Real example: Gravity near Earth
        Newton's gravity is non-linear:
        F = -GMm/r²
        But near Earth's surface (r ≈ constant), we approximate it as LINEAR:
        F ≈ mg  (constant acceleration)
        Why? Because understanding the linear part (mg) first gives intuition, then we add non-linear corrections.
    - [x] Matrix representation of transformations
        -A matrix encodes a linear transformation by showing where each basis vector goes. Since any vector can be reconstructed from basis vectors, the matrix captures the entire transformation
    - [x] Range, kernel, rank-nullity theorem
        -Kernel a.k.a null space is the set of input vectors that are mapped to zero. Nullity is the dimension of the Kernal
        -Range is the set of all output vectors produced
        -Rank is the dimension of the Range, i.e the number of dimensions retained after transformation
        -Rank-nullity theorem: Rank + Nullity = n (input dimension). Dimensions that survive + Dimensions that die = Total inputs
    - [x] Composition and invertibility
        -Composition applies transformations in sequence by first multiplying all transformation matrices together into one composed matrix, then applying it to vectors. Composition is computationally faster than sequential transformation when many vectors are transformed (k>n).  
        -Invertibility - a transformation is invertible if and only if its has a full rank - rank = n,  determinant != 0, nullity = 0.
- - [x] Eigenvalues and eigenvectors
    -Null space are vectors that map to zero (destroyed by transformation) while Eigenvectors are the vectors that survive and get scaled by Eigenvalue λ.
    - [x] Characteristic equation
        -Matrix A applied to a vector v only scales it by Eigenvalue λ
            => A.v = λ.v 
            => A.v - λ.v = 0 
            => (A - λI) . v = 0
            meaning, matrix A - λI maps vector v to zero
            => det (A - λI) must be zero 
            Solve det (A - λI) = 0 to find all values of λ that make A - λI collapse space.
            Plug each Eigenvalue λ back in (A - λI).v = 0 to find Eigenvectors v.
    - [x] Eigendecomposition
        -It is a method to break down a square matrix into smaller pieces by decomposing it into eigenvectors and eigenvalues. Not all square matrices have Eigendecomposition. For non-square matrix decomposition, refer to SVD.
        -Decompose symmetric square matrices:
            -A = V · D · Vᵀ
                -A = Symmetric square matrix
                -V = Matrix of orthonormal Eigenvectors in columns
                -D = Diagonal matrix of Eigenvalues
                -Calculation steps:
                    1. Start:        A·vᵢ = λᵢ·vᵢ  (for each i)
                    2. Stack:        A·V = [A·v₁  A·v₂  ...  A·vₙ]
                    3. Substitute:   A·V = [λ₁·v₁  λ₂·v₂  ...  λₙ·vₙ]
                    4. Factor:       A·V = V·D
                    5. Multiply Vᵀ:  A·V·Vᵀ = V·D·Vᵀ
                    6. Use Vᵀ·V=I:   A = V·D·Vᵀ
                -  The order V · D · Vᵀ is FORCED by:
                    1. Eigenvalue definition forces A·v = λ·v (not v·λ = A·v)
                    2. Stacking forces A·V = V·D (not D·V)
                    3. Isolating A forces multiplication by Vᵀ on right
                    No choice in the ordering. Mathematics dictates it.
            -Spectral theorem:
                -Every symmetric matrix has Eigendecomposition
                -Decomposes matrix into its spectrum of Eigenvalues, hence spectral.
        -Decompose non-symmetric square matrices:
            - Eigenvectors are linearly independent -> A = V·D·V⁻¹ 
            - Eigenvectors are linearly DEPENDENT -> No Eigendecomposition exists. Can not form invertible V (V⁻¹ doesn't exist). Use SVD instead.
    - [x] Diagonalization
        -It is a method to efficiently compute power of matrices A<sup>n</sup>, where n is the power i.e. A multiplied by itself by n times. Note: Must need n linearly independent Eigenvalues, not all matrices are diagonalizable e.g. matrices with repeated Eigenvalues with insufficient Eigenvectors
            A<sup>n</sup> = P . D<sup>n</sup> . P<sup>-1</sup>
                P = Eigenvectors as columns
                D = Diagonal matrix of Eigenvalues. Calculating D<sup>n</sup>  is easier.
                P<sup>-1</sup> = 1/det(P) * adj(P) , adj(P) = transpose of the cofactor matrix. 
                    In practice, computers use Gaussian elimination ([ P | I ] ->[ I | P<sup>-1</sup> ]) or LU decomposition to calculate inverse as  calculations using adjugate are inaccurate and unstable. [ P | I ] - augmented matrix
           - Steps:
               1. Calculate all Eigenvalues by solving det(A - λI) = 0
               2. Put back each Eigenvalue in the equation  (A - λI).v = 0
               3. Solve for Eigenvectors v  (set one Eigenvector as 1)
                   - Note 1: If there are multiple identical equations → Use any one. It happens because A - λI is rank deficient
                   - Note 2: If there are linearly independent equations → Use them all (they give different constraints)
             4. Build P using Eigenvectors as columns
             5. Build the diagonal matrix D with Eigenvalues in the same order as the Eigenvector. First Eigenvector goes with First Eigenvalue. Order must match.
             6. Compute P-1 from 1/det(P) * adj(P) or Gaussian Elimination
             7. Finally, compute P. D<sup>n</sup>.P<sup>-1</sup> 
    - [x] Spectral theorem for symmetric matrices
        -Symmetric matrices are square matrices which are equal to its transpose
            A (n x n) = A<sup>T</sup> (n x n)
        -Spectral theorem is used to find the Principal Directions a.k.a. Eigenvectors and their spread/variance a.k.a. Eigenvalues in symmetrical matrices.
            A = Q . D . Q<sup>T</sup> 
                Q = Matrix of orthonormal Eigenvectors as columns, vectors that are perpendicular to each other and have unit length.
                D = Diagonal matrix of Eigenvalues
                Orthonormality guarantees Q<sup>T</sup> == -1 (automatic inverse)
        -Unlike diagonalization, spectral theorem doesn't require inverse to be calculated as Q<sup>T</sup> automatically becomes Q<sup>-1</sup>
- - [x] Positive definite matrices
    - Ensure positive second order quantities such as variance, uncertainty, and spread,  because uncertainty/variance measure "HOW MUCH things spread out" — and you can't spread out by a negative amount. e.g. The dots are LESS than zero distance apart - doesn't make sense.
    - [x] Definition and properties
        x<sup>T</sup> (Ax) > 0 for all x≠0 => The matrix A transforms the vector x in the same direction (acute angle). Matrix A never flips any vector backwards (obtuse angle). Dot product of the input vector and its transformed version is positive. x<sup>T</sup> (Ax) = 0 implies the matrix A is most positive semi-definite meaning, the matrix A rotates the input vector x by 90<sup>o</sup> 

| Type                  | Condition                           | Eigenvalues | Geometric Shape                  |
| --------------------- | ----------------------------------- | ----------- | -------------------------------- |
| Positive definite     | x<sup>T</sup> A x > 0 for all x ≠ 0 | All λᵢ > 0  | Bowl (minimum)                   |
| Positive semidefinite | x<sup>T</sup> A x ≥ 0 for all x     | All λᵢ ≥ 0  | Flat bowl (some flat directions) |
| Negative definite     | x<sup>T</sup> A x < 0 for all x ≠ 0 | All λᵢ < 0  | Upside-down bowl (maximum)       |
| Negative semidefinite | x<sup>T</sup> A x ≤ 0 for all x     | All λᵢ ≤ 0  | Flat upside-down bowl            |
| Indefinite            | x<sup>T</sup> A x can be + or -     | Mixed signs | Saddle point                     |

- 
    - [x] Relationship to eigenvalue
        -The matrix is positive definite if and only if all its Eigenvalues are positive. To determine if a matrix is positive definite, instead of checking whether x<sup>T</sup> A x > 0, solve for 
        (A - λI) . v = 0. If all Eigenvalues λ are positive, then the matrix is positive definite.
    - [x] Covariance matrix
        -Covariance matrix Σ describes the geometric shape of the data cloud.
            - Circular shape (Σ = [[[a, 0], [0, a]]]): Data spreads equally in all directions
            - Ellipse shape (Σ = [a, b], [b, c]): Data stretches more in one direction
            - Thin ellipse/line (Σ = high correlation): Almost all data along one line
        -Σ doesn't describe the center (μ) of the data cloud, it just describes the shape and spread around the center for.
        -Data follows normal distribution (N): D ~ N (μ,  Σ)
        -Covariance matrix are the systematic tool to find the dimensions of the input data that really matter. 
        -It is a summary that shows how each variable behaves alone and how each pair of variables move together. The covariance matrix Σ comprises:
                Diagonal elements - spreads (variances) of individual variables, how they vary on their own
                Off-diagonal elements - joint relationships (covariances, how the variables move together
        -Property 1: Covariance matrix is always equal to its transpose Σ = Σ<sup>T</sup> i.e. a covariance matrix is always symmetric, cov (x<sub>i</sub> , x<sub>j</sub>) = cov (x<sub>j</sub> , x<sub>i</sub>) 
        -Σ = [var (x<sub>i</sub>)     cov (x<sub>i</sub> , x<sub>j</sub>)]
           [cov (x<sub>j</sub> , x<sub>i</sub>)      var (x<sub>j</sub>)]
        -Property 2: Covariance matrix is always positive semidefinite, i.e. all its Eigenvalues are equal to or greater than zero.
        -Compute the Covariance Matrix: 
                1. Collect data → matrix X (n observations × d variables)
                2. Compute means → μ for each variable
                3. Center data → Xᶜ = X - μ (subtract mean from each column)
                4. Multiply → Xᶜᵀ Xᶜ (pairs and sums all deviations)
                5. Scale → Σ = (1/n) Xᶜᵀ Xᶜ (the covariance matrix)
        -Compute Eigenvalues:
                6. Set up → det(Σ - λI) = 0
                7. Solve → find all λ values that satisfy this equation
                8. Interpret → each λ tells "how much variance along principal direction i"
        -Compute Eigenvectors:
                9. Set up → (Σ - λI)v = 0 for each eigenvalue λ
                10. Solve → Gaussian elimination on this homogeneous system
                11. Extract → the direction v (normalized to unit length)
                12. Interpret → v tells "which blend of original variables creates direction i"
    - [x] Cholesky decomposition
        -Cholesky decomposition enables efficient generation of correlated synthetic data from  uncorrelated random samples.
            -How the process works: 
                1. Decompose covariance matrix Σ into lower triangular matrix such that         Σ = L L<sup>T</sup>
                    1.1 Initialize L as lower triangular matrix such that L[i , j] = 0 for all i < j
                    1.2 Compute each diagonal element L <sub>i</sub> <sub>i</sub> =  square root (√) of (Σ i i - sum of squares of all elements to the left in row i)
                    1.3 Compute each off-diagonal element L i <sub> j </sub> (i > j) = (Σ <sub>i</sub> <sub>j</sub> - sum of products of elements at same column positions in rows i and j to the left) divided by (/) L <sub>j</sub> <sub> j </sub> 
                2. Generate one standard normalized random sample, z
                3. Synthetic data x is generated as x = L  z  (multiplication of Cholesky matrix and the sample)
- - [x]  Principal direction problems
    -Principal direction is an Eigenvector in the data where things spread out the most. Eigenvalue tell us how much the data spreads in the principal direction.
    - [x] Finding directions of maximum variance
          1. Arrange input vectors as column vectors in a matrix 
            - X (n samples × p features)
          2. Center the data by computing mean of each column and subtracting it from all rows
            - X<sub>centered</sub>= X - mean(X)
          3. Compute the Gram matrix as the dot product of centered data with its transpose
            - X<sub>centered</sub>ᵀ · X<sub>centered</sub>
          4. Calculate covariance matrix Σ by dividing the Gram matrix by the number of samples
            - Σ = (1/n) · X<sub>centered</sub>ᵀ · X<sub>centered</sub>
          5. Find eigenvalues by solving the characteristic equation
            - det(Σ - λI) = 0
            - This yields all eigenvalues λ₁, λ₂, ..., λₚ
          6. Find eigenvectors by substituting each eigenvalue back into the system
            - (Σ - λᵢI) · v = 0
            - Solve for vector v (the eigenvector corresponding to λᵢ)
          7. Normalize each eigenvector to unit length by dividing by its norm
            - v<sub>normalized</sub> = v / ||v||
            - This normalized vector is the principal direction
            - The corresponding eigenvalue λᵢ is the variance along that direction
    - [x] Connection to eigenvalue problems
        -Spectral Decomposition or Eigendecomposition: Any symmetric matrix can be reconstructed from its Eigenvectors and Eigenvalues.
        -Eigenvalue decomposition is not possible for non-square matrix because Eigenvalues can only be defined for square matrices.
            - Eigenvalue equation A . v = λ · v is only possible when size of A . v is same as v. 
        -Since any covariance matrix Σ is symmetric, it can be decomposed as 
            Σ = V . D . V<sup>T</sup>
            V  - Matrix of orthonormal Eigenvectors of Σ as columns
            D - Diagonal matrix of Eigenvalues of Σ  
            V<sup>T</sup> = V<sup>-1</sup> (automatic inverse) as V is orthonormal matrix
        -Treat it as an optimization problem and solve it using calculus/Lagrange multipliers or solve it as eigenvalue problems. Both are same
    - [x] PCA applications
        -PCA is applied wherever we want to understand or transform high-dimensional data. PCA is used for:
        1. Dimensionality reduction - Reduce dimensions while minimizing information loss. Useful for reducing computation/storage.
        2. Data visualization  - project high-dimensional data to 3D/2D and explore
        3. Anomaly detection - learn principal directions and find anomalies/outliers
        4. Noise removal - keep high-variance principal components (signal) and discard low-variances (noise)
        5. Feature engineering - remove correlated features and retain uncorrelated principal components. 
        -PCA is only useful if the features are correlated i.e. if the off-diagonal elements of the covariance matrix Σ are not zero..
        -PCA transforms correlated to uncorrelated
- - [x] Singular value decomposition (SVD)
    -SVD extends the idea of Eigendecomposition to rectangular matrices. It is a mathematical tool for decomposing any matrix. 
    -Data-driven problems frequently produce rectangular equation systems - more equations than unknowns, or vice versa, hence, the need for SVD. Traditional physics/engineering (e.g. Newton's laws, FEA) often involve square equation systems - regular inverse works.
    -SVD breaks a matrix into simple ranked pieces by importance. Keep the top pieces that capture the most variance and discard the rest - a trade-off between accuracy and compression.
    -The central idea: Every matrix decomposes into three simple operations (matrices) - rotation,  stretch (Diagonal Matrix), rotation - which are easy to visualize geometrically.
    - [x] A = U . Σ<sub>svd</sub> . V<sup>T</sup> decomposition
        -V<sup>T</sup> - Rotation (input to "good" coordinates)
        -Σ<sub>svd</sub> - Stretch (diagonal matrix)
        -U - Rotation (output coordinates)
        -Σ<sub>svd</sub> ≠ Σ in PCA , which is covariance matrix
         -Proof that any matrix can be written as  A = U . Σ_svd . V<sup>T</sup>
             1. Take a matrix A and its transpose Aᵀ, and compute their product Aᵀ . A.  This converts any rectangular matrix A in to a square
             2. Since Aᵀ.A is square, it has Eigendecomposition  (Aᵀ.A).vᵢ = λᵢ.vᵢ
             3. Calculate norm:
                a. Multiply both sides by vᵢᵀ from left: vᵢᵀ . (Aᵀ . A) . vᵢ = vᵢᵀ . λᵢ . vᵢ
                b. Regroup by associativity rule: (vᵢᵀ . Aᵀ) . (A . vᵢ) = λᵢ . vᵢᵀ . vᵢ
                c. Apply transpose rule: (A . vᵢ)ᵀ . (A  . vᵢ) = λᵢ . (vᵢᵀ . vᵢ)
                d. Recognize both sides as norms: ||A . vᵢ||² = λᵢ . ||vᵢ||²
                e. Eigenvectors in Eigendecomposition are normalized to unit length: ||vᵢ||² = 1
                f. Simplify: ||A . vᵢ||² = λᵢ , therefore ||A . vᵢ|| = √λᵢ =: σᵢ
                g. Define uᵢ as normalized vector: Normalize A . vᵢ as A . vᵢ / ||A . vᵢ|| and equate it to a arbitrary new variable uᵢ
                h. Substitute σᵢ: uᵢ = A . vᵢ / ||A . vᵢ||  or uᵢ = A . vᵢ / σᵢ
                i. Rearrange: A . vᵢ = uᵢ . σᵢ
                j. Stack all columns: [A.vᵢ] = [uᵢ.σᵢ] , or A . V = U . Σ<sub>svd</sub>  (where Σ<sub>svd</sub> is the diagonal matrix of singular values σᵢ)
                k. Solve for A: A = U.Σ<sub>svd</sub>.Vᵀ 
    - [x] Relationship to eigenvalues
        -V = Eigenvectors of A<sup>T</sup> . A
        -U = Eigenvectors of A . A<sup>T</sup>
        -σᵢ² = Non-zero Eigenvalues (same for both A<sup>T</sup> . A and A . A<sup>T</sup>)
        -Caveat: Total Eigenvalue count differs (n for A<sup>T</sup>·A, m for A·A<sup>T</sup>)
        Σ<sub>svd</sub> = Diagonal matrix of singular values σᵢ (not σᵢ²)
            - σᵢ = 0 -> matrix is singular, true singularity. dimension is lost
            - Small non-zero σᵢ  -> nearly singular. weakest direction. closest to collapse
            - Large σᵢ -> most important direction 
    - [x] Applications (low-rank approximation, pseudoinverse)
        -Low-rank approximation
            -Make a simpler version of the data that's good enough i.e. keep the most important pieces and throw away the rest.
            -Favored in machine learning / data science for data exploration and compression - understand patterns, compress data, and generalize to new data. 
            -For e.g. in photo compression, out of the 1000 original pieces of info, keep top 50 pieces containing most important details. 
            -Result - 95% look the same but uses 10x less storage
        -Pseudoinverse
            -Solve equations when normal solving doesn't work.
            -Favored in engineering/scientific computing for computation and problem solving - where we need exact solutions to physical equations. 
            - Low rank occasionally used for compression.
            -Gives coefficient values. Doesn't reveal underlying structure
            -Fixes 2 problems:
                -Problem A: Too many equations
                    -You have 100 measurements but only 2 unknowns
                    -Equations contradict each other (no perfect answer)
                    -Pseudoinverse finds "best fit" answer
                -Problem B: Too few equations
                    -You have 2 equations but 3 unknowns
                    -Infinite possible answers
                    -Pseudoinverse picks the simplest one (smallest values)
- [ ]Least squares problems
    -Real-world data is messy. We want to fine a line (or curve) that fits them as well as possible.
    -Find the line where the sum of squared vertical distances (errors) from the data points to the line is minimum.
    -Squaring errors: 1. makes -ve errors positive, 2. punishes big errors more then small ones.
    - [ ]Normal equations: Aᵀ Ax = Aᵀ b
        -In a overdetermined system, where number of equations are far more than number of unknowns, there is no one exact solution. 
        -Goal is to fit the best line across the data points to minimize the error, ||Ax - b||²
        -Derivation: 
            1. ||Ax - b||² 
                    =  (Ax - b)ᵀ (Ax - b)
                    = (Ax)ᵀ(Ax) - (Ax)ᵀb - bᵀ(Ax) + bᵀb
                    = xᵀ.Aᵀ.A.x - xᵀ.Aᵀ.b - bᵀ.A.x + bᵀ.b
                    = xᵀ.Aᵀ.A.x - (xᵀ.Aᵀ.b)ᵀ - bᵀ.A.x + bᵀ.b (A scalar is equal to its transpose)
                    = xᵀ.Aᵀ.A.x - bᵀ.A.x - bᵀ.A.x + bᵀ.b
                    = xᵀ.Aᵀ.A.x - 2.bᵀ.A.x + bᵀ.b
            2. Since we are solving an optimization problem, i.e. finding x that minimizes the error , we use calculus function to find the minimum by taking derivative and set to zero.
            3. Take derivative w.r.t. x and set to zero. In other words,
                    d/dx [xᵀ.Aᵀ.A.x - 2.bᵀ.A.x + bᵀ.b] = 0
                    2AᵀAx - 2Aᵀb = 0
                    AᵀAx = Aᵀb  ← Normal equation
    - [ ]QR decomposition method
    - [ ]Geometric interpretation
- [ ]Inversion of block matrices
    - [ ]Block matrix inversion formulas
    - [ ]Computational efficiency techniques
- [ ]Schur complement identity
    - [ ]Definition and formula
    - [ ]Use in block matrix inversion
    - [ ]Applications in optimization
- [ ]Sherman-Morrison-Woodbury
    - [ ]Rank-1 and low-rank updates to inverses
    - [ ]Formula: (A + UCV)^(-1)
    - [ ]Computational efficiency for small updates
- [ ]Matrix determinant lemma
    - [ ]det(A + UV^T) in terms of det(A)
    - [ ]Connection to Sherman-Morrison-Woodbury
    - [ ]Applications in statistics and optimization

  INTRODUCTION TO PROBABILITY
- [ ]Random variables
- [ ]Joint probability
- [ ]Marginal probability
- [ ]Conditional probability
- [ ]Bayes' rule
- [ ]Independence
- [ ]Expectation and variance
- [ ]Covariance and correlation

  PROBABILITY DISTRIBUTIONS
- [ ]Bernoulli distribution
- [ ]Beta distribution
- [ ]Categorical distribution
- [ ]Dirichlet distribution
- [ ]Univariate normal distribution
- [ ]Normal-inverse-gamma distribution
- [ ]Multivariate normal distribution
- [ ]Normal-inverse-Wishart distribution
- [ ]Conjugacy

  FITTING PROBABILITY DISTRIBUTIONS
- [ ]Maximum likelihood
- [ ]Maximum a posteriori
- [ ]Bayesian approach
- [ ]Example: fitting normal
- [ ]Example: fitting categorical
- [ ]Model selection and cross-validation

  THE NORMAL DISTRIBUTION
- [ ]Types of covariance matrix
- [ ]Decomposition of covariance
- [ ]Linear transformations
- [ ]Marginal distributions
- [ ]Conditional distributions
- [ ]Product of two normals
- [ ]Change of variable formula

  OPTIMIZATION
- [ ]Gradient-based optimization
- [ ]Convexity
- [ ]Steepest descent
- [ ]Newton's method
- [ ]Gauss-Newton method
- [ ]Line search
- [ ]Conjugate gradient
- [ ]Stochastic gradient descent and noise properties
- [ ]Learning rate schedules (step decay, exponential, cosine, OneCycle)
- [ ]Reparameterization
- [ ]Constrained optimization

  BAYESIAN OPTIMIZATION
- [ ]Gaussian processes for BO
- [ ]Acquisition functions (EI, PI, UCB)
- [ ]Incorporating noise
- [ ]Kernel choice
- [ ]Learning GP parameters
- [ ]Tips, tricks, and limitations
- [ ]Beta-Bernoulli bandit
- [ ]Random forests for BO
- [ ]Tree-Parzen estimators

  DIFFERENTIAL EQUATIONS IN ML
- [ ]Ordinary differential equations (ODEs)
- [ ]Stochastic differential equations (SDEs)
- [ ]Solving ODEs: Euler method, Runge-Kutta methods
- [ ]ODEs and gradient descent
- [ ]SDEs in stochastic gradient descent
- [ ]ODEs in residual networks
- [ ]ODEs and SDEs in diffusion models
- [ ]Physics-informed machine learning

  CAPSTONE PROJECT 1
- [ ]Implement optimization algorithms from scratch
- [ ]Compare convergence on test functions

  ================================================================================
  PHASE II – NEURAL NETWORK FUNDAMENTALS
  ================================================================================

  INTRODUCTION TO NEURAL NETWORKS
- [ ]Biological inspiration
- [ ]Perceptrons
- [ ]Activation functions (sigmoid, tanh, ReLU, variants)
- [ ]Multi-layer perceptrons
- [ ]Universal approximation theorem
- [ ]Forward propagation

  TRAINING NEURAL NETWORKS
- [ ]Loss functions (MSE, cross-entropy, custom losses)
- [ ]Backpropagation algorithm
- [ ]Computational graphs
- [ ]Gradient descent variants (SGD, momentum, Nesterov)
- [ ]Adaptive learning rates (AdaGrad, RMSprop, Adam, AdamW)
- [ ]Learning rate schedules
- [ ]Batch, mini-batch, and stochastic training

  REGULARIZATION AND NORMALIZATION
- [ ]L1 and L2 regularization
- [ ]Dropout and variants
- [ ]Early stopping
- [ ]Data augmentation
- [ ]Batch normalization
- [ ]Layer normalization
- [ ]Group normalization
- [ ]Weight normalization
- [ ]Spectral normalization

  NETWORK ARCHITECTURES I: CNNS
- [ ]Convolution operation
- [ ]Pooling layers
- [ ]CNN architectures (LeNet, AlexNet, VGG)
- [ ]Residual networks (ResNet)
- [ ]Inception networks
- [ ]DenseNet
- [ ]EfficientNet
- [ ]1x1 convolutions and bottlenecks

  NETWORK ARCHITECTURES II: RNNS
- [ ]Recurrent neural networks
- [ ]Backpropagation through time
- [ ]Vanishing/exploding gradients
- [ ]Long short-term memory (LSTM)
- [ ]Gated recurrent units (GRU)
- [ ]Bidirectional RNNs
- [ ]Sequence-to-sequence models
- [ ]Encoder-decoder architectures

  PRACTICAL DEEP LEARNING
- [ ]Data preprocessing and normalization
- [ ]Train/validation/test splits
- [ ]Debugging neural networks
- [ ]Weight initialization strategies
- [ ]Gradient checking
- [ ]Dealing with overfitting/underfitting
- [ ]Transfer learning
- [ ]Fine-tuning strategies
- [ ]Model compression (pruning, quantization, distillation)

  DEEP LEARNING FRAMEWORKS
- [ ]PyTorch fundamentals
- [ ]TensorFlow/Keras fundamentals
- [ ]Building custom layers and models
- [ ]Dataset and DataLoader patterns
- [ ]Automatic differentiation
- [ ]GPU acceleration
- [ ]Distributed training basics
- [ ]Model saving and loading

  CAPSTONE PROJECT 2
- [ ]Build and train CNN for image classification
- [ ]Build and train RNN for text generation

  ================================================================================
  PHASE III – CORE MACHINE LEARNING
  ================================================================================

  LEARNING AND INFERENCE
- [ ]Discriminative models
- [ ]Generative models
- [ ]Example: regression
- [ ]Example: classification
- [ ]Bias-variance tradeoff
- [ ]No free lunch theorem

  REGRESSION MODELS
- [ ]Linear regression
- [ ]Bayesian linear regression
- [ ]Non-linear regression
- [ ]Bayesian non-linear regression
- [ ]The kernel trick
- [ ]Gaussian process regression
- [ ]Sparse linear regression
- [ ]Relevance vector regression
- [ ]Neural network regression

  CLASSIFICATION MODELS
- [ ]Logistic regression
- [ ]Bayesian logistic regression
- [ ]Non-linear logistic regression
- [ ]Support vector machines
- [ ]Gaussian process classification
- [ ]Relevance vector classification
- [ ]Incremental fitting: boosting and trees
- [ ]Multi-class logistic regression
- [ ]Neural network classification

  MODEL EVALUATION AND SELECTION
- [ ]Evaluation metrics (accuracy, precision, recall, F1, AUC-ROC)
- [ ]Confusion matrices
- [ ]Calibration metrics (Expected Calibration Error, Brier score)
- [ ]Generative model metrics (FID, IS, FVD, CLIP-score)
- [ ]Human evaluation protocols
- [ ]Cross-validation strategies
- [ ]Hyperparameter tuning (see Phase I, 7. Bayesian Optimization)
- [ ]Grid search and random search
- [ ]Learning curves
- [ ]Benchmarking and leaderboards

  GRAPHICAL MODELS
- [ ]Conditional independence
- [ ]Directed graphical models (Bayesian networks)
- [ ]Undirected graphical models (Markov networks)
- [ ]Inference in graphical models
- [ ]Sampling in graphical models
- [ ]Learning in graphical models

  MODELS FOR SEQUENCES
- [ ]Hidden Markov models
- [ ]Viterbi algorithm
- [ ]Forward-backward algorithm
- [ ]Belief propagation
- [ ]Sum product algorithm
- [ ]Extension to trees
- [ ]Graphs with loops

  MODELS FOR STRUCTURED DATA
- [ ]Markov random fields
- [ ]MAP inference in binary pairwise MRFs
- [ ]Graph cuts
- [ ]Multi-label pairwise MRFs
- [ ]Alpha-expansion algorithm
- [ ]Conditional random fields

  CAPSTONE PROJECT 3
- [ ]Build end-to-end ML pipeline
- [ ]Implement hyperparameter tuning
- [ ]Perform comprehensive evaluation

  ================================================================================
  PHASE IV – UNSUPERVISED AND GENERATIVE MODELS
  ================================================================================

  CLASSICAL UNSUPERVISED LEARNING
- [ ]K-means clustering
- [ ]Hierarchical clustering
- [ ]DBSCAN
- [ ]Principal component analysis (PCA)
- [ ]Independent component analysis (ICA)
- [ ]t-SNE
- [ ]UMAP

  MODELING COMPLEX DATA DENSITIES
- [ ]Hidden variables
- [ ]Expectation maximization
- [ ]Mixture of Gaussians
- [ ]The t-distribution
- [ ]Factor analysis
- [ ]The EM algorithm in detail

  AUTOENCODERS
- [ ]Basic autoencoders
- [ ]Denoising autoencoders
- [ ]Sparse autoencoders
- [ ]Contractive autoencoders
- [ ]Stacked autoencoders
- [ ]Applications of autoencoders

  VARIATIONAL AUTOENCODERS
- [ ]Non-linear latent variable models
- [ ]Evidence lower bound (ELBO)
- [ ]ELBO properties
- [ ]Variational approximation
- [ ]The variational autoencoder
- [ ]Reparameterization trick
- [ ]β-VAE and disentanglement
- [ ]Conditional VAE

  GENERATIVE ADVERSARIAL NETWORKS
- [ ]GAN framework
- [ ]Training dynamics
- [ ]Mode collapse
- [ ]DCGAN
- [ ]Wasserstein GAN
- [ ]Conditional GAN
- [ ]StyleGAN and variants
- [ ]Progressive growing
- [ ]GAN evaluation metrics (FID, IS, precision/recall)

  NORMALIZING FLOWS
- [ ]Normalizing flows introduction
- [ ]Elementwise and linear flows
- [ ]Planar and radial flows
- [ ]Coupling and autoregressive flows
- [ ]Coupling functions
- [ ]Residual flows
- [ ]Infinitesimal (continuous) flows
- [ ]Neural ODE flows
- [ ]Datasets and performance

  DIFFUSION MODELS
- [ ]Forward diffusion process
- [ ]Reverse diffusion process
- [ ]Denoising diffusion probabilistic models (DDPM)
- [ ]Score-based generative models
- [ ]Denoising diffusion implicit models (DDIM)
- [ ]Latent diffusion models
- [ ]Classifier-free guidance
- [ ]Conditioning mechanisms
- [ ]Evaluation metrics (see 5.9; also FVD for video)

  CAPSTONE PROJECT 4
- [ ]Implement VAE for image generation
- [ ]Implement GAN for image generation
- [ ]Implement diffusion model for image generation
- [ ]Compare all three approaches

  ================================================================================
  PHASE V – BAYESIAN MACHINE LEARNING
  ================================================================================

  BAYESIAN FUNDAMENTALS
- [ ]Maximum likelihood review
- [ ]Maximum a posteriori review
- [ ]The Bayesian approach
- [ ]Example: 1D linear regression
- [ ]Practical concerns
- [ ]Computational challenges

  GAUSSIAN PROCESSES
- [ ]Function space view
- [ ]Gaussian processes
- [ ]Kernels and kernel trick
- [ ]Inference
- [ ]Non-linear regression
- [ ]GP classification
- [ ]Sparse GPs
- [ ]Deep GPs

  BAYESIAN NEURAL NETWORKS
- [ ]Sampling vs. variational approximation
- [ ]MCMC methods (Metropolis-Hastings, Hamiltonian MC)
- [ ]SWAG and MultiSWAG
- [ ]Bayes by backprop
- [ ]Monte Carlo dropout
- [ ]Laplace approximation
- [ ]Ensemble methods

  NEURAL NETWORK GAUSSIAN PROCESSES
- [ ]Shallow networks as GPs
- [ ]Neural network Gaussian processes
- [ ]NNGP kernel
- [ ]Kernel regression
- [ ]Network stability

  UNCERTAINTY QUANTIFICATION
- [ ]Aleatoric vs. epistemic uncertainty
- [ ]Prediction intervals
- [ ]Calibration
- [ ]Out-of-distribution detection
- [ ]Conformal prediction

  CAPSTONE PROJECT 5
- [ ]Build Bayesian models for uncertainty-aware predictions

  ================================================================================
  PHASE VI – DEEP LEARNING THEORY
  ================================================================================

  GRADIENT FLOW
- [ ]Gradient flow
- [ ]Evolution of residual
- [ ]Evolution of parameters
- [ ]Evolution of model predictions
- [ ]Evolution of prediction covariance

  NEURAL TANGENT KERNEL
- [ ]Infinite width neural networks
- [ ]Training dynamics
- [ ]Empirical NTK for shallow networks
- [ ]Analytical NTK for shallow networks
- [ ]Empirical NTK for deep networks
- [ ]Analytical NTK for deep networks

  NTK APPLICATIONS
- [ ]Trainability
- [ ]Convergence bounds
- [ ]Evolution of parameters
- [ ]Evolution of predictions
- [ ]NTK Gaussian processes
- [ ]NTK and generalizability

  GENERALIZATION THEORY
- [ ]PAC learning
- [ ]VC dimension
- [ ]Rademacher complexity
- [ ]Implicit regularization
- [ ]Double descent
- [ ]Lottery ticket hypothesis
- [ ]Neural collapse

  OPTIMIZATION LANDSCAPE
- [ ]Loss surface geometry
- [ ]Critical points and saddle points
- [ ]Mode connectivity
- [ ]Sharp vs. flat minima
- [ ]The role of overparameterization

  CAPSTONE PROJECT 6
- [ ]Empirical study of neural network training dynamics

  ================================================================================
  PHASE VII – ATTENTION AND TRANSFORMERS
  ================================================================================

  ATTENTION MECHANISMS
- [ ]Sequence-to-sequence attention
- [ ]Bahdanau attention
- [ ]Luong attention
- [ ]Self-attention
- [ ]Multi-head attention
- [ ]Cross-attention
- [ ]Attention visualizations

  TRANSFORMERS I: ARCHITECTURE
- [ ]Dot-product self-attention
- [ ]Scaled dot-product attention
- [ ]Position encoding
- [ ]Multiple heads
- [ ]Feed-forward networks
- [ ]Transformer block
- [ ]Encoder architecture
- [ ]Decoder architecture
- [ ]Encoder-decoder architecture

  TRANSFORMERS II: POSITIONAL ENCODINGS
- [ ]Sinusoidal position embeddings
- [ ]Learned position embeddings
- [ ]Relative vs. absolute position embeddings
- [ ]Rotary position embeddings (RoPE)
- [ ]ALiBi
- [ ]Extending to longer sequences

  TRANSFORMERS III: EFFICIENT ATTENTION
- [ ]Attention complexity analysis
- [ ]Reducing attention matrix size
- [ ]Making attention sparse (Sparse Transformer)
- [ ]Linformer and Performer
- [ ]Kernelized attention
- [ ]Flash Attention
- [ ]Attention as an RNN
- [ ]Local attention windows
- [ ]Longformer and BigBird

  TRANSFORMERS IV: ADVANCED ARCHITECTURES
- [ ]Attention as a hypernetwork
- [ ]Attention as a routing network
- [ ]Attention and graphs (Graph Transformers)
- [ ]Attention and convolutions
- [ ]Attention and gating
- [ ]Attention and memory retrieval
- [ ]Memory-augmented transformers

  TRANSFORMERS V: TRAINING
- [ ]Tricks for training transformers
- [ ]Why these tricks are required
- [ ]Removing layer normalization
- [ ]Balancing residual dependencies
- [ ]Reducing optimizer variance
- [ ]Pre-layer normalization vs. post-layer normalization
- [ ]Training deeper transformers
- [ ]Initialization strategies

  CAPSTONE PROJECT 7
- [ ]Implement transformer from scratch
- [ ]Train on machine translation task

  ================================================================================
  PHASE VIII – LARGE LANGUAGE MODELS
  ================================================================================

  INTRODUCTION TO LLMS
- [ ]What is an LLM?
- [ ]Tokenization (BPE, WordPiece, SentencePiece)
- [ ]Language modeling objective
- [ ]Autoregressive vs. masked language models
- [ ]Model scaling laws
- [ ]Emergent abilities

  LLM ARCHITECTURES
- [ ]GPT architecture and variants
- [ ]BERT and bidirectional models
- [ ]T5 and encoder-decoder models
- [ ]Decoder-only vs. encoder-decoder tradeoffs
- [ ]Architecture innovations (grouped-query attention, sliding window)
- [ ]Mixture of Experts (MoE)
- [ ]State space models (Mamba, S4)

  PRETRAINING LLMS
- [ ]Pretraining objectives
- [ ]Dataset curation and filtering
- [ ]Training infrastructure
- [ ]Distributed training strategies
- [ ]Mixed precision training
- [ ]Gradient accumulation
- [ ]Checkpointing and recovery

  FINE-TUNING LLMS
- [ ]Supervised fine-tuning (SFT)
- [ ]Instruction tuning
- [ ]Task-specific fine-tuning
- [ ]Parameter-efficient fine-tuning (PEFT)
- [ ]LoRA and QLoRA
- [ ]Prefix tuning and prompt tuning
- [ ]Adapter layers

  ALIGNMENT AND RLHF
- [ ]AI alignment problem
- [ ]Reward modeling
- [ ]Proximal Policy Optimization (PPO)
- [ ]Reinforcement learning from human feedback (RLHF)
- [ ]Direct preference optimization (DPO)
- [ ]Constitutional AI
- [ ]Red teaming and safety

  PROMPTING AND IN-CONTEXT LEARNING
- [ ]Zero-shot prompting
- [ ]Few-shot prompting
- [ ]Chain-of-thought prompting
- [ ]Tree of thoughts
- [ ]Prompt engineering techniques
- [ ]In-context learning theory
- [ ]Retrieval-augmented generation: indexing, chunking, retrieval, reranking, grounding, evaluation
- [ ]Retrieval corpus construction and dense indexing (FAISS, HNSW)

  LLM INFERENCE AND OPTIMIZATION
- [ ]Inference challenges
- [ ]Request batching and continuous batching
- [ ]Paged KV cache and memory management
- [ ]Tensor parallelism and pipeline parallelism
- [ ]Prefix caching
- [ ]Dynamic routing for Mixture of Experts
- [ ]Speculative decoding
- [ ]Quantization for inference
- [ ]Constrained generation (grammar-based, regex, JSON)
- [ ]Attention-free alternatives (RWKV, Retentive Network)
- [ ]Model distillation
- [ ]Serving infrastructure

  NOTABLE LLMS AND APPLICATIONS
- [ ]GPT family
- [ ]LLaMA and open-source models
- [ ]Claude architecture insights
- [ ]Gemini and multimodal integration
- [ ]Domain-specific LLMs
- [ ]Code generation models
- [ ]LLM agents and tool use

  CAPSTONE PROJECT 8
- [ ]Fine-tune open-source LLM for specific task
- [ ]Implement RAG system
- [ ]Evaluate retrieval (Recall@k, MRR, nDCG)
- [ ]Evaluate answer faithfulness (exact match, F1, groundedness)

  ================================================================================
  PHASE IX – COMPUTER VISION
  ================================================================================

  CLASSICAL COMPUTER VISION
- [ ]Image processing (filtering, edges, corners)
- [ ]Whitening and histogram equalization
- [ ]Feature extraction (SIFT, SURF, HOG)
- [ ]Dimensionality reduction for vision

  CAMERA GEOMETRY
- [ ]Pinhole camera model
- [ ]Camera distortion
- [ ]Coordinate systems
- [ ]Extrinsic and intrinsic parameters
- [ ]3D inference from images
- [ ]Camera calibration

  GEOMETRIC TRANSFORMATIONS
- [ ]Euclidean transformations
- [ ]Similarity transformations
- [ ]Affine transformations
- [ ]Projective transformations
- [ ]Transformation estimation
- [ ]RANSAC and robust fitting
- [ ]Image warping and stitching

  MULTIPLE VIEW GEOMETRY
- [ ]Two-view geometry
- [ ]Essential and fundamental matrices
- [ ]Epipolar geometry
- [ ]Stereo reconstruction
- [ ]Rectification
- [ ]Multiview reconstruction
- [ ]Structure from motion

  MODERN CNN ARCHITECTURES
- [ ]Object detection (R-CNN, Fast R-CNN, Faster R-CNN)
- [ ]YOLO family
- [ ]Single-shot detectors (SSD, RetinaNet)
- [ ]Semantic segmentation (FCN, U-Net, DeepLab)
- [ ]Instance segmentation (Mask R-CNN)
- [ ]Panoptic segmentation
- [ ]Feature Pyramid Networks
- [ ]Dataset bias and annotation quality
- [ ]Detection and segmentation metrics (mAP, mAP@.50:.95 COCO, latency, throughput)

  VISION TRANSFORMERS
- [ ]Vision Transformer (ViT) architecture
- [ ]Patch embeddings
- [ ]Hybrid CNN-Transformer models
- [ ]Swin Transformer
- [ ]DeiT and distillation
- [ ]Masked autoencoders (MAE)
- [ ]Self-supervised vision models
- [ ]Vision-language evaluation and metrics (VQAv2, TextVQA, RefCOCO, BLEU, CIDEr, SPICE, CLIP-score)

  3D COMPUTER VISION
- [ ]3D representations (voxels, point clouds, meshes)
- [ ]PointNet and PointNet++
- [ ]3D convolutions
- [ ]Neural radiance fields (NeRF)
- [ ]3D Gaussian splatting
- [ ]Depth estimation
- [ ]Camera pose estimation
- [ ]SLAM basics

  VIDEO UNDERSTANDING
- [ ]Temporal modeling in video
- [ ]3D CNNs (C3D, I3D)
- [ ]Two-stream networks
- [ ]Action recognition
- [ ]Video object detection
- [ ]Video transformers
- [ ]Temporal action localization

  CAPSTONE PROJECT 9
- [ ]Build object detection and segmentation pipeline

  ================================================================================
  PHASE X – NATURAL LANGUAGE PROCESSING
  ================================================================================

  NLP FUNDAMENTALS
- [ ]Text preprocessing
- [ ]Tokenization approaches
- [ ]Word embeddings (Word2Vec, GloVe)
- [ ]Contextual embeddings (ELMo)
- [ ]Subword embeddings
- [ ]Evaluation metrics for NLP

  SEQUENCE MODELING
- [ ]RNN-based sequence models
- [ ]LSTM and GRU for NLP
- [ ]Encoder-decoder for seq2seq
- [ ]Attention in seq2seq
- [ ]Beam search and decoding strategies

  PRETRAINED LANGUAGE MODELS
- [ ]Transfer learning in NLP
- [ ]BERT and variants (RoBERTa, ALBERT, DeBERTa)
- [ ]GPT series
- [ ]T5 and unified text-to-text
- [ ]XLNet
- [ ]ELECTRA
- [ ]Model distillation (DistilBERT)

  NEURAL TEXT GENERATION
- [ ]Neural language generation basics
- [ ]Encoder-decoder models
- [ ]Training objectives
- [ ]Beam search
- [ ]Sampling strategies (top-k, nucleus)
- [ ]RL fine-tuning for generation
- [ ]Minimum risk training
- [ ]SeaRNN and RAML

  PARSING AND STRUCTURED PREDICTION
- [ ]Context-free grammars (CFGs)
- [ ]Probabilistic CFGs
- [ ]Parsing algorithms (CKY)
- [ ]Semiring parsing
- [ ]Inside-outside algorithm
- [ ]Neural parsing
- [ ]Dependency parsing

  NLP APPLICATIONS
- [ ]Text classification
- [ ]Named entity recognition
- [ ]Question answering
- [ ]Summarization
- [ ]Machine translation
- [ ]Sentiment analysis
- [ ]Information extraction
- [ ]Dialogue systems

  ADVANCED NLP TOPICS
- [ ]Multilingual models
- [ ]Cross-lingual transfer
- [ ]Low-resource NLP
- [ ]Knowledge-grounded generation
- [ ]Commonsense reasoning
- [ ]Reasoning and planning with LLMs
- [ ]Retrieval metrics (Recall@k, MRR, nDCG)
- [ ]Hallucination detection and grounding scores

  CAPSTONE PROJECT 10
- [ ]Build complete NLP application (QA system or chatbot)

  ================================================================================
  PHASE XI – MULTIMODAL LEARNING
  ================================================================================

  VISION-LANGUAGE MODELS
- [ ]Image captioning
- [ ]Visual question answering
- [ ]Vision-and-language pretraining
- [ ]CLIP architecture and training
- [ ]ALIGN and contrastive learning
- [ ]BLIP and unified models
- [ ]Flamingo and few-shot multimodal learning

  MULTIMODAL TRANSFORMERS
- [ ]Cross-modal attention
- [ ]ViLBERT and LXMERT
- [ ]Unified transformers (UNITER, VILLA)
- [ ]Vision-language encoders vs. fusion models
- [ ]Multimodal pretraining objectives

  TEXT-TO-IMAGE GENERATION
- [ ]Conditional image generation
- [ ]DALL-E and discrete VAE
- [ ]Stable Diffusion architecture
- [ ]Text conditioning in diffusion models
- [ ]ControlNet and spatial control
- [ ]Image editing with diffusion

  MULTIMODAL APPLICATIONS
- [ ]Image-text retrieval
- [ ]Video captioning
- [ ]Audio-visual learning
- [ ]Document understanding
- [ ]Medical multimodal AI
- [ ]Embodied AI

  CAPSTONE PROJECT 11
- [ ]Build vision-language model for image retrieval or captioning

  ================================================================================
  PHASE XII – REINFORCEMENT LEARNING
  ================================================================================

  RL FUNDAMENTALS
- [ ]Markov decision processes (MDPs)
- [ ]Value functions and Bellman equations
- [ ]Dynamic programming
- [ ]Monte Carlo methods
- [ ]Temporal difference learning
- [ ]Q-learning
- [ ]SARSA
- [ ]Exploration vs. exploitation

  DEEP REINFORCEMENT LEARNING
- [ ]Deep Q-Networks (DQN)
- [ ]Double DQN and improvements
- [ ]Policy gradient methods
- [ ]REINFORCE algorithm
- [ ]Actor-critic methods
- [ ]A3C and A2C
- [ ]Proximal Policy Optimization (PPO)
- [ ]Trust Region Policy Optimization (TRPO)

  ADVANCED RL
- [ ]Deterministic policy gradient (DDPG)
- [ ]Twin Delayed DDPG (TD3)
- [ ]Soft Actor-Critic (SAC)
- [ ]Model-based RL
- [ ]World models
- [ ]Offline RL and dataset quality (CQL, IQL)
- [ ]Imitation learning
- [ ]Inverse reinforcement learning
- [ ]Safety constraints in RL
- [ ]Reward hacking diagnostics

  MULTI-AGENT RL
- [ ]Multi-agent environments
- [ ]Cooperative vs. competitive settings
- [ ]Nash equilibria
- [ ]Multi-agent communication
- [ ]QMIX and value decomposition

  TRANSFORMERS IN RL
- [ ]Challenges in RL
- [ ]Advantages of transformers for RL
- [ ]Decision Transformer
- [ ]Trajectory Transformer
- [ ]Representation learning with transformers
- [ ]Transition and reward modeling
- [ ]Policy learning with transformers
- [ ]Interpretability in RL transformers

  TEMPORAL MODELS
- [ ]Kalman filter
- [ ]Smoothing
- [ ]Extended Kalman filter
- [ ]Unscented Kalman filter
- [ ]Particle filtering
- [ ]Applications in robotics

  CAPSTONE PROJECT 12
- [ ]Train RL agent for game or robotics simulation

  ================================================================================
  PHASE XIII – RESPONSIBLE AI
  ================================================================================

  BIAS AND FAIRNESS
- [ ]Sources of bias in ML
- [ ]Types of fairness
- [ ]Demographic parity
- [ ]Equality of odds
- [ ]Equality of opportunity
- [ ]Individual fairness
- [ ]Bias detection methods
- [ ]Bias mitigation strategies
- [ ]Fairness-aware learning

  EXPLAINABILITY I: LOCAL METHODS
- [ ]Why explainability matters
- [ ]Local post-hoc explanations
- [ ]Counterfactual explanations
- [ ]LIME (Local Interpretable Model-agnostic Explanations)
- [ ]Anchors
- [ ]SHAP (SHapley Additive exPlanations)
- [ ]Integrated gradients
- [ ]Attention visualization

  EXPLAINABILITY II: GLOBAL METHODS
- [ ]Feature importance
- [ ]Partial Dependence Plots (PDP)
- [ ]Individual Conditional Expectation (ICE)
- [ ]Accumulated Local Effects (ALE)
- [ ]Aggregate SHAP
- [ ]Prototype and criticism methods
- [ ]Surrogate models
- [ ]Inherently interpretable models

  DIFFERENTIAL PRIVACY I
- [ ]Privacy foundations
- [ ]Definition of differential privacy
- [ ]ε-differential privacy
- [ ]Laplace mechanism
- [ ]Gaussian mechanism
- [ ]Composition theorems
- [ ]Privacy budget

  DIFFERENTIAL PRIVACY II
- [ ]Differential privacy in ML
- [ ]DP-SGD (Differentially Private SGD)
- [ ]PATE (Private Aggregation of Teacher Ensembles)
- [ ]DPGAN
- [ ]PateGAN
- [ ]Privacy-utility tradeoffs
- [ ]Privacy auditing

  AI SAFETY AND SECURITY
- [ ]Adversarial examples
- [ ]Adversarial training
- [ ]Certified defenses
- [ ]Model extraction attacks
- [ ]Data poisoning
- [ ]Backdoor attacks
- [ ]Membership inference
- [ ]Model inversion
- [ ]Jailbreak and prompt-injection testing
- [ ]Data leakage detection and testing
- [ ]Red-teaming evaluation suites and adversarial prompts
- [ ]Model spec compliance testing

  AI ETHICS AND GOVERNANCE
- [ ]Ethical principles in AI
- [ ]Accountability and transparency
- [ ]Human oversight
- [ ]Environmental impact of AI
- [ ]AI regulations (GDPR, EU AI Act)
- [ ]Documentation (model cards, datasheets)
- [ ]Stakeholder engagement

  CAPSTONE PROJECT 13
- [ ]Audit model for bias
- [ ]Build explanations
- [ ]Implement privacy-preserving training

  ================================================================================
  PHASE XIV – ADVANCED TOPICS AND META-LEARNING
  ================================================================================

  FEW-SHOT LEARNING I
- [ ]Problem formulation
- [ ]Meta-learning framework
- [ ]Metric learning approaches
- [ ]Matching networks
- [ ]Prototypical networks
- [ ]Relation networks
- [ ]Siamese networks

  FEW-SHOT LEARNING II
- [ ]Optimization-based meta-learning
- [ ]MAML (Model-Agnostic Meta-Learning)
- [ ]Reptile
- [ ]LSTM-based meta-learning
- [ ]Memory-augmented neural networks
- [ ]Neural Turing Machines
- [ ]SNAIL

  FEW-SHOT AND ZERO-SHOT WITH LLMS
- [ ]In-context learning as meta-learning
- [ ]Prompt-based few-shot learning
- [ ]Zero-shot generalization
- [ ]Instruction following
- [ ]Transfer across modalities

  NEURAL ARCHITECTURE SEARCH
- [ ]NAS problem formulation
- [ ]Search spaces
- [ ]Reinforcement learning for NAS
- [ ]Gradient-based NAS (DARTS)
- [ ]Efficient NAS methods
- [ ]Once-for-all networks
- [ ]AutoML frameworks

  CONTINUAL AND LIFELONG LEARNING
- [ ]Catastrophic forgetting
- [ ]Regularization-based approaches (EWC, SI)
- [ ]Replay-based methods
- [ ]Dynamic architectures
- [ ]Meta-learning for continual learning
- [ ]Task-incremental and class-incremental learning

  GRAPH NEURAL NETWORKS
- [ ]Graph representation
- [ ]Graph convolutions
- [ ]Graph attention networks
- [ ]Message passing neural networks
- [ ]Graph pooling
- [ ]Applications (molecular property prediction, social networks)
- [ ]Knowledge graphs

  ADVANCED OPTIMIZATION AND SEARCH
- [ ]Boolean logic and satisfiability
- [ ]SAT solvers (DPLL, CDCL)
- [ ]CNF and Tseitin transformation
- [ ]Applications (graph coloring, scheduling)
- [ ]Binary neural network fitting
- [ ]Factor graph representation
- [ ]Survey propagation
- [ ]SMT solvers

  CAPSTONE PROJECT 14
- [ ]Implement meta-learning system for rapid task adaptation

  ================================================================================
  PHASE XV – ML SYSTEMS AND PRODUCTION
  ================================================================================

  MLOPS FUNDAMENTALS
- [ ]ML lifecycle
- [ ]Experiment tracking
- [ ]Model versioning
- [ ]Data versioning
- [ ]CI/CD for ML
- [ ]Model registry
- [ ]Data governance and PII handling
- [ ]License compliance for datasets and models
- [ ]Reproducibility (seeds, environments, containers)
- [ ]Evaluation harnesses and benchmarking

  MODEL DEPLOYMENT
- [ ]Model serving architectures
- [ ]REST APIs for models
- [ ]Batch vs. real-time inference
- [ ]Model packaging (ONNX, TorchScript)
- [ ]Edge deployment
- [ ]Model monitoring
- [ ]A/B testing
- [ ]SLA vs. SLO vs. error budgets

  SCALABLE TRAINING
- [ ]Data parallelism
- [ ]Model parallelism
- [ ]Pipeline parallelism
- [ ]Distributed data loading
- [ ]Gradient accumulation
- [ ]Mixed precision training
- [ ]ZeRO optimization

  INFRASTRUCTURE AND TOOLS
- [ ]Cloud platforms (AWS, GCP, Azure)
- [ ]Kubernetes for ML
- [ ]Docker containers
- [ ]GPU management
- [ ]Workflow orchestration (Airflow, Kubeflow)
- [ ]Feature stores
- [ ]ML platforms (SageMaker, Vertex AI)

  PRODUCTION BEST PRACTICES
- [ ]Data quality monitoring
- [ ]Model performance monitoring
- [ ]Drift detection
- [ ]Model retraining strategies
- [ ]Logging and debugging
- [ ]Cost optimization and cost-per-request dashboards
- [ ]Security in production

  REAL-WORLD CASE STUDIES
- [ ]Recommendation systems at scale
- [ ]Search and ranking systems
- [ ]Computer vision in production
- [ ]NLP systems deployment
- [ ]Real-time ML systems
- [ ]Handling data and model drift

  CAPSTONE PROJECT 15
- [ ]Deploy end-to-end ML system with monitoring and CI/CD
- [ ]Define SLOs (latency P95/P99, throughput, cost per 1k tokens)
- [ ]Implement drift alarms
- [ ]Create rollback plan

  ================================================================================
  FINAL CAPSTONE: COMPREHENSIVE AI PROJECT
  ================================================================================

- [ ]Problem definition and scoping
- [ ]Data collection and preprocessing
- [ ]Model selection and development
- [ ]Training, evaluation, and optimization
- [ ]Bias and fairness auditing
- [ ]Model explanation and documentation
- [ ]Deployment and monitoring
- [ ]Presentation and documentation
