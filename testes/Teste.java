public class TesteCompilador {
    private int contador;
    private String nome;

    public TesteCompilador(String nome, int contador) {
        this.nome = nome;
        this.contador = contador;
    }

    public int somarAte(int limite) {
        int soma = 0;

        for (int i = 1; i <= limite; i++) {
            if (i % 2 == 0) {
                soma += i;
            } else {
                soma += 1;
            }
        }

        return soma;
    }

    public String classificar(int valor) {
        switch (valor) {
            case 1:
                return "Um";
            case 2:
                return "Dois";
            default:
                return "Outro";
        }
    }

    public void executar() {
        int resultado = somarAte(10);
        boolean valido = resultado > 0 && contador >= 0;

        if (valido) {
            System.out.println(nome + ": " + resultado);
        } else {
            System.out.println("Resultado invalido");
        }

        while (contador < 3) {
            contador++;
        }

        int[] numeros = {1, 2, 3, 4, 5};
        for (int numero : numeros) {
            System.out.println(classificar(numero));
        }

        try {
            if (resultado == 0) {
                throw new IllegalArgumentException("Resultado zero");
            }
        } catch (IllegalArgumentException erro) {
            System.out.println(erro.getMessage());
        } finally {
            System.out.println("Execucao finalizada");
        }
    }

    public static void main(String[] args) {
        TesteCompilador teste = new TesteCompilador("Aluno", 0);
        teste.executar();
    }
}
