package br.edu.unijorge;

import java.util.*;

public class Completo {
    private static final int LIMITE = 10;
    private List<String> nomes = new ArrayList<>();
    private Map<String, Integer> mapa = new HashMap<String, Integer>();

    public Completo() {
        this.nomes = null;
    }

    public static int soma(int a, int b) {
        return a + b;
    }

    @Override
    public String toString() {
        return "Completo";
    }

    public static void main(String[] args) {
        int[] v = new int[10];
        int total = 0;
        boolean flag = true;
        for (int i = 0; i < LIMITE; i++) {
            v[i] = i * 2;
            total += v[i];
        }
        if (total > 50) {
            System.out.println("Grande: " + total);
        } else {
            System.out.println("Pequeno");
        }
        int k = 0;
        while (k < 3) {
            k++;
        }
        do {
            k--;
        } while (k > 0);
        switch (k) {
            case 0:
                flag = false;
                break;
            default:
                flag = true;
        }
        total = soma(total, 5);
    }
}
