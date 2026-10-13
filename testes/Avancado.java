package app;

import java.util.*;
import java.util.function.Function;

/**
 * Arquivo "difícil": recursos modernos do Java.
 */
@SuppressWarnings("unchecked")
public class Avancado<T extends Comparable<T>> implements Runnable {
    private final Map<String, List<Integer>> indice = new HashMap<>();
    private static final double PI = 3.14159;
    private int[][] matriz = {{1, 2}, {3, 4}};

    static {
        System.out.println("bloco estático");
    }

    enum Cor { VERMELHO, VERDE, AZUL }

    interface Forma {
        double area();
        default String nome() { return "forma"; }
    }

    record Ponto(int x, int y) { }

    public static int soma(int... valores) {
        int total = 0;
        for (int v : valores) {
            total = total + v;
        }
        return total;
    }

    @Override
    public void run() {
        String texto = """
            bloco de texto
            com "aspas"
            """;
        int a = 10, b = 20, c;
        c = a > b ? a : b;
        c = (a + b) * -2 / (b - a) % 7;
        Function<Integer, Integer> dobra = x -> x * 2;
        Runnable r = new Runnable() {
            @Override
            public void run() {
                int interno = 1;
                interno = interno + 1;
            }
        };
        try (Scanner sc = new Scanner(System.in)) {
            int lido = sc.nextInt();
            lido = lido + a;
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            c = 0;
        }
        externo:
        for (int i = 0; i < 10; i++) {
            if (i == 5) break externo;
            else continue;
        }
        switch (c) {
            case 1 -> c = 2;
            default -> c = 3;
        }
        Cor cor = Cor.AZUL;
        Object o = texto;
        if (o instanceof String s && !s.isEmpty()) {
            c = s.length();
        }
        char ch = 'x';
        int codigo = ch + 1;
        long l = 0xFFL + 0b1010 + 1_000_000L;
        double d = .5 + 1e-3 + 2.0d;
        c >>>= 2;
        c = c << 1;
    }

    public static void main(String[] args) {
        new Avancado<String>().run();
    }
}
