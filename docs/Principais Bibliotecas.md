## Principais Bibliotecas e Ferramentas para Integração
LLamaSharp (C# / .NET): A principal biblioteca para rodar modelos GGUF (Llama, Mistral, Phi) em projetos C# e Unity.

## ONNX Runtime (Microsoft): Ideal para tarefas como visão computacional, classificação de texto ou modelos menores convertidos para .onnx.

## LLMUnity: Pacote voltado para Unity que roda llama.cpp localmente sem precisar de internet ou chaves de API.

## In-Process (Biblioteca Nativa C# / C++)
Seu aplicativo carrega a IA diretamente na própria memória.

Como funciona: Você usa uma biblioteca wrapper em C# (como LLamaSharp ou Microsoft.ML.OnnxRuntime) dentro do código do seu projeto.

## Vantagens: Não requer processos externos ou portas de rede locais abertas; tudo roda nativamente em uma única DLL.

Como implementar em C#:

using LLama.Common;
using LLama;

var parameters = new ModelParams("caminho/para/o/modelo.gguf") {
    ContextSize = 1024,
    GpuLayerCount = 20 // Envia camadas para a GPU
};
using var model = LLamaWeights.LoadFromFile(parameters);
using var context = model.CreateContext(parameters);
var executor = new InteractiveExecutor(context);

// Gera a resposta diretamente no app
await foreach (var text in executor.InferAsync("Olá, quem é você?")) {
    Console.Write(text);
}

