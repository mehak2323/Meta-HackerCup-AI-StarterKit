import java.io.*;
import java.util.*;

public class optimal {

    static class Item {
        long amazingness;
        int bricks;
        double ratio; // For sorting, can use cross-multiplication for precision
        int originalIndex;

        public Item(long amazingness, int bricks, int originalIndex) {
            this.amazingness = amazingness;
            this.bricks = bricks;
            this.ratio = (double) amazingness / bricks;
            this.originalIndex = originalIndex;
        }
    }

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new FileReader("input.txt"));
        PrintWriter pw = new PrintWriter(new BufferedWriter(new FileWriter("output.txt")));

        int T = Integer.parseInt(br.readLine());
        for (int t = 1; t <= T; t++) {
            StringTokenizer st = new StringTokenizer(br.readLine());
            int N = Integer.parseInt(st.nextToken());
            long M = Long.parseLong(st.nextToken());

            long[] A = new long[N + 1];
            st = new StringTokenizer(br.readLine());
            for (int i = 1; i <= N; i++) {
                A[i] = Long.parseLong(st.nextToken());
            }

            long[] S = new long[N + 1]; // S[j] = sum(A_1 to A_j)
            long maxSVal = 0;
            for (int i = 1; i <= N; i++) {
                S[i] = S[i - 1] + A[i];
                maxSVal = Math.max(maxSVal, S[i]);
            }

            // Find item with best amazingness/bricks ratio
            // Using a list to sort is not strictly necessary, just need the best one.
            Item bestItem = null;
            for (int j = 1; j <= N; j++) {
                // To avoid floating point issues, compare S_a/a vs S_b/b as S_a*b vs S_b*a
                // S_j can be 10^15, j can be 1000. S_j*j can be 10^18, fits in long.
                if (bestItem == null || S[j] * bestItem.bricks > bestItem.amazingness * j) {
                    bestItem = new Item(S[j], j, j);
                }
            }

            long bestS = bestItem.amazingness;
            int bestK = bestItem.bricks;

            // DP state: dp[b] = maximum amazingness for 'b' bricks
            // Max bricks for DP part: N*N.
            // Max amazingness for DP part: M + maxSVal (cap to avoid long overflow)
            int maxBricksDP = N * N;
            // Cap dp values at M + maxSVal. Any amazingness beyond M + maxSVal is effectively infinite for our purpose.
            // This is because maxSVal is the largest possible amazingness from a single item.
            // If we have M + maxSVal, we can satisfy M, and any remainder M_rem will be less than maxSVal.
            long maxAmazingnessCap = M + maxSVal; 
            if (maxAmazingnessCap < M) { // Handle overflow if M + maxSVal exceeds Long.MAX_VALUE
                maxAmazingnessCap = Long.MAX_VALUE;
            }


            long[] dp = new long[maxBricksDP + 1];
            Arrays.fill(dp, Long.MIN_VALUE); // Use MIN_VALUE to indicate unreachable
            dp[0] = 0;

            // O(N * maxBricksDP) DP using deque optimization
            // For each item j (cost j, value S[j])
            for (int j = 1; j <= N; j++) {
                // For each remainder 'rem' when dividing by j
                for (int rem = 0; rem < j; rem++) {
                    Deque<Integer> deque = new LinkedList<>();
                    // Iterate through 'b' values that have the same remainder 'rem'
                    // b = rem + q*j
                    for (int q = 0; rem + q * j <= maxBricksDP; q++) {
                        int b = rem + q * j;
                        
                        // Calculate normalized amazingness for current b
                        // dp[b] - q * S[j]
                        // Only consider reachable states for comparison
                        long currentNormalizedAmazingness = Long.MIN_VALUE;
                        if (dp[b] != Long.MIN_VALUE) {
                            currentNormalizedAmazingness = dp[b] - (long)q * S[j];
                        }

                        // Remove elements from deque that are worse than current
                        while (!deque.isEmpty()) {
                            int prev_b = deque.getLast();
                            long prev_q = (prev_b - rem) / j;
                            long prevNormalizedAmazingness = dp[prev_b] - prev_q * S[j];
                            
                            // If current is better or equal, remove previous
                            if (prevNormalizedAmazingness <= currentNormalizedAmazingness) {
                                deque.removeLast();
                            } else {
                                break;
                            }
                        }
                        
                        // Add current to deque if reachable
                        if (dp[b] != Long.MIN_VALUE) {
                            deque.addLast(b);
                        }

                        // Update dp[b] using the best element in deque
                        // dp[b] = dp[deque.getFirst()] + (q - (deque.getFirst() - rem)/j) * S[j]
                        if (!deque.isEmpty()) {
                            int best_prev_b = deque.getFirst();
                            long best_prev_q = (best_prev_b - rem) / j;
                            
                            if (dp[best_prev_b] != Long.MIN_VALUE) { // Only update if reachable
                                long potentialAmazingness = dp[best_prev_b] + (q - best_prev_q) * S[j];
                                dp[b] = Math.max(dp[b], potentialAmazingness);
                                dp[b] = Math.min(dp[b], maxAmazingnessCap); // Cap the amazingness
                            }
                        }
                    }
                }
            }

            long minTotalBricks = Long.MAX_VALUE;
            int finalBopt = -1;
            long finalQopt = -1;

            // Iterate through all possible 'b' values from DP table
            for (int b = 0; b <= maxBricksDP; b++) {
                if (dp[b] == Long.MIN_VALUE) { // Unreachable state
                    continue;
                }

                long currentTotalBricks;
                long currentQ;

                if (dp[b] >= M) {
                    currentTotalBricks = b;
                    currentQ = 0; // No need to use best_item further
                } else {
                    long M_rem = M - dp[b];
                    currentQ = (M_rem + bestS - 1) / bestS; // ceil division
                    currentTotalBricks = b + currentQ * bestK;
                }

                if (currentTotalBricks < minTotalBricks) {
                    minTotalBricks = currentTotalBricks;
                    finalBopt = b;
                    finalQopt = currentQ;
                }
            }

            // Reconstruct y_j values
            long[] y = new long[N + 1];
            if (finalQopt > 0) {
                y[bestK] += finalQopt;
            }

            int currentBricksForBopt = finalBopt;
            // Reconstruct y_j for the DP part (finalBopt bricks)
            // Iterate j from N down to 1
            for (int j = N; j >= 1; j--) {
                while (currentBricksForBopt >= j) {
                    long prevAmazingness = Long.MIN_VALUE;
                    if (currentBricksForBopt - j >= 0) {
                        prevAmazingness = dp[currentBricksForBopt - j];
                    }

                    boolean canTakeItemJ = false;
                    if (prevAmazingness != Long.MIN_VALUE) {
                        // Check if taking item j leads to the current state
                        // This is true if dp[currentBricksForBopt - j] + S[j] (potentially capped) equals dp[currentBricksForBopt]
                        long potentialAmazingness = prevAmazingness + S[j];
                        if (potentialAmazingness >= maxAmazingnessCap) { // If it would be capped
                            potentialAmazingness = maxAmazingnessCap;
                        }

                        if (potentialAmazingness == dp[currentBricksForBopt]) {
                            canTakeItemJ = true;
                        }
                    }

                    if (canTakeItemJ) {
                        y[j]++;
                        currentBricksForBopt -= j;
                        // currentAmazingnessForBopt is implicitly handled by currentBricksForBopt
                        // and dp table. We don't need to explicitly track it.
                    } else {
                        break;
                    }
                }
            }

            // Convert y_j to x_i
            long[] x = new long[N + 1];
            x[N] = y[N];
            for (int i = N - 1; i >= 1; i--) {
                x[i] = y[i] + x[i + 1];
            }

            pw.println("Case #" + t + ": " + minTotalBricks);
            StringBuilder sb = new StringBuilder();
            for (int i = 1; i <= N; i++) {
                sb.append(x[i]);
                if (i < N) {
                    sb.append(" ");
                }
            }
            pw.println(sb.toString());
        }

        br.close();
        pw.close();
    }
}