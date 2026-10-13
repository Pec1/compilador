// comentario de linha
/* comentario
   multilinha */
/** javadoc
 * @author equipe
 */
public class Lexico {
    void teste() {
        String s = "a\"b\n";
        char c1 = 'a';
        char c2 = '\n';
        char c3 = '\'';
        int n1 = 10;
        double n2 = 3.14;
        float n3 = 3.14f;
        long n4 = 10L;
        int n5 = 0x1F;
        double n6 = 1e10;
        int n7 = 1_000;
        boolean b = n1 == n5 != false;
        b = n1 <= n5 && n1 >= n5 || !b;
        n1++; n1--;
        n1 += 1; n1 -= 1; n1 *= 2; n1 /= 2;
        n1 = b ? 1 : 0;
        Runnable r = () -> System.out.println("x");
        Runnable m = System.out::println;
        n1 = n1 << 1 >> 1 >>> 1;
        n1 >>= 1;
        b = s instanceof String;
    }
}
