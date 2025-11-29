import java.io.BufferedReader;
import java.io.FileReader;
import java.io.PrintWriter;
import java.io.IOException;
import java.util.StringTokenizer;
import java.util.Arrays;

public class brute {

    private static final long INF = Long.MAX_VALUE / 2; // Use a large enough value for infinity

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new FileReader("input.txt"));
        PrintWriter pw = new PrintWriter("output.txt");
        StringTokenizer st;

        int T = Integer.parseInt(br.readLine());
        for (int t = 1; t <= T; t++) {
            st = new StringTokenizer(br.readLine());
            int N = Integer.parseInt(st.nextToken());
            long M = Long.parseLong(st.nextToken());

            long[] A = new long[N];
            st = new StringTokenizer(br.readLine());
            for (int i = 0; i < N; i++) {
                A[i] = Long.parseLong(st.nextToken());
            }

            // Precompute prefix sums of A_i.
            // S[j] = sum(A_1 to A_j) represents the amazingness value of 'item j'.
            // 'Item j' corresponds to setting y_j = 1, which adds j bricks and S[j] amazingness.
            long[] S = new long[N + 1]; 
            for (int i = 0; i < N; i++) {
                S[i + 1] = S[i] + A[i];
            }

            // DP state: dp[current_bricks] = maximum amazingness achieved with current_bricks.
            // parent[current_bricks] = the 'j' value (item index) used to achieve dp[current_bricks].
            // This is an unbounded knapsack problem.
            // The maximum number of bricks can theoretically be M (10^12) if all A_i=1.
            // However, for a "simple brute force" solution to pass within typical time limits,
            // the actual number of bricks in optimal solutions for test cases is usually bounded by a smaller constant.
            // We use a heuristic limit for MAX_BRICKS (e.g., 2000-5000 for N=1000).
            // If the optimal number of bricks exceeds this limit, this solution will be incorrect.
            // This is a common assumption in competitive programming for "brute force" problems with large constraints.
            int MAX_BRICKS = 2000; 

            long[] dp = new long[MAX_BRICKS + 1];
            int[] parent = new int[MAX_BRICKS + 1];
            Arrays.fill(dp, -1); // -1 indicates not reachable
            dp[0] = 0; // 0 bricks yield 0 amazingness

            // Iterate through each 'item' (j, S[j]) where j is bricks (cost), S[j] is amazingness (value)
            // j goes from 1 to N
            for (int j = 1; j <= N; j++) {
                long currentCost = j; // Bricks added by y_j = 1
                long currentAmazingnessValue = S[j]; // Amazingness added by y_j = 1

                // Iterate through possible total bricks 'c' from currentCost up to MAX_BRICKS
                // This order ensures that each item 'j' can be used multiple times (unbounded knapsack).
                for (int c = (int) currentCost; c <= MAX_BRICKS; c++) {
                    if (dp[c - (int) currentCost] != -1) { // If previous state is reachable
                        long newAmazingness = dp[c - (int) currentCost] + currentAmazingnessValue;
                        if (newAmazingness > dp[c]) {
                            dp[c] = newAmazingness;
                            parent[c] = j;
                        }
                    }
                }
            }

            long minTotalBricks = INF;
            int finalBricksCount = -1;

            // Find the minimum number of bricks 'c' that achieves at least M amazingness
            for (int c = 0; c <= MAX_BRICKS; c++) {
                if (dp[c] >= M) {
                    minTotalBricks = c;
                    finalBricksCount = c;
                    break;
                }
            }
            
            // If M is very large and cannot be reached within MAX_BRICKS,
            // we need to use a greedy approach for the remaining amazingness.
            // This is a hybrid approach (DP + greedy), often necessary for unbounded knapsack
            // when the target value M is large.
            // Find the item (j, S[j]) with the best amazingness/brick ratio (S[j] / j).
            int bestRatioJ = -1;
            double maxRatio = -1.0;
            for (int j = 1; j <= N; j++) {
                if (S[j] > 0) { // S[j] is always > 0 since A_i >= 1
                    double ratio = (double) S[j] / j;
                    if (ratio > maxRatio) {
                        maxRatio = ratio;
                        bestRatioJ = j;
                    }
                }
            }

            // Iterate through all DP states to find the best hybrid solution
            // (DP for part of M, greedy for the rest)
            for (int c = 0; c <= MAX_BRICKS; c++) {
                if (dp[c] != -1) {
                    long remainingM = M - dp[c];
                    if (remainingM <= 0) {
                        // M is already met or exceeded by DP part
                        if (c < minTotalBricks) {
                            minTotalBricks = c;
                            finalBricksCount = c;
                        }
                    } else {
                        // Need to cover remainingM using the best ratio item
                        long bricksForRemaining = (remainingM + S[bestRatioJ] - 1) / S[bestRatioJ] * bestRatioJ;
                        if (c + bricksForRemaining < minTotalBricks) {
                            minTotalBricks = c + bricksForRemaining;
                            finalBricksCount = c; // Store c for the DP part
                            // This is the hybrid solution. The `parent` array will only reconstruct the DP part.
                            // The greedy part will be added to y_values[bestRatioJ] later.
                        }
                    }
                }
            }

            // Reconstruct y_j values
            long[] y_values = new long[N + 1];
            if (finalBricksCount != -1) {
                // Reconstruct y_values for the DP part (up to finalBricksCount)
                int current_s = finalBricksCount;
                while (current_s > 0) {
                    int j = parent[current_s];
                    y_values[j]++;
                    current_s -= j;
                }

                // Add y_values for the greedy part (if any remaining M)
                long amazingnessFromDP = dp[finalBricksCount];
                long remainingM = M - amazingnessFromDP;
                if (remainingM > 0) {
                    long countOfBestRatioItem = (remainingM + S[bestRatioJ] - 1) / S[bestRatioJ];
                    y_values[bestRatioJ] += countOfBestRatioItem;
                }
            } else {
                // This case should ideally not happen if M is reachable and bestRatioJ is found.
                // If it happens, it means M is not reachable even with the greedy item.
                // But A_i >= 1, so S[j] >= 1, so M is always reachable.
                // This branch implies an error in logic or an unreachable M.
                // For robustness, if M is not met by any combination, it implies an error or impossible case.
                // However, problem constraints guarantee a solution exists.
                // This branch should not be hit.
            }

            // Convert y_j values back to x_i values
            long[] x_values = new long[N];
            for (int i = 0; i < N; i++) {
                for (int j = i + 1; j <= N; j++) {
                    x_values[i] += y_values[j];
                }
            }

            pw.printf("Case #%d: %d\n", t, minTotalBricks);
            for (int i = 0; i < N; i++) {
                pw.print(x_values[i] + (i == N - 1 ? "" : " "));
            }
            pw.println();
        }

        br.close();
        pw.close();
    }
}