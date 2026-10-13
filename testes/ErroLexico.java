public class ErroLexico {
    void f() {
        int a = 1 # 2;
        int b = `3`;
        int c = 4;
        String s = "sem fechar;
        int d = 5;
    }
}
