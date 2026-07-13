using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

internal static class Program
{
    private const string ExtractorId = "tools/csharp_semantic_overlay_probe/Program.cs";
    private const string ExtractorVersion = "0.1.0";
    private const string ArtifactRole = "intentgraph-experimental-csharp-semantic-relation-overlay";
    private const string ArtifactStatus = "intentgraph-experimental-csharp-semantic-relation-overlay-extracted";
    private const string ArtifactScope = "experimental-csharp-semantic-relation-overlay-readonly";

    private sealed record SourceLocation(int LineStart, int LineEnd, int ColumnStart, int ColumnEnd);

    private sealed record Fact(
        string Id,
        string Kind,
        string SourceFile,
        string SourceDigest,
        SourceLocation? SourceLocation);

    private sealed record ExtractorInfo(
        string Id,
        string Version,
        string Mode,
        bool Deterministic,
        bool SemanticResolution,
        bool SourceBuildAllowed,
        bool BroadExtractor);

    private sealed record CodeFacts(
        string ArtifactRole,
        string Status,
        string Scope,
        string ProfileId,
        string CodeFactsVersion,
        string SourceRoot,
        string SourceRootKind,
        ExtractorInfo Extractor,
        SortedDictionary<string, string> SourceDigests,
        List<Fact> Facts);

    private sealed record ResolvedRelation(string Id, string Kind, string From, string To, string Confidence);

    private sealed record Diagnostics(int CompilationErrorCount, int CompilationWarningCount, int LocalDeclarationCount);

    private sealed record Authority(
        bool SourceReadFromSnapshotOnly,
        bool TargetRepositoryMutation,
        bool TargetBuildExecuted,
        bool TargetRestoreExecuted,
        bool NetworkRequired,
        bool CredentialAccessAllowed,
        bool GraphMutationApplied);

    private sealed record SemanticOverlay(
        string ArtifactRole,
        string Status,
        string Scope,
        string ProfileId,
        string SourceRoot,
        string SourceRootKind,
        ExtractorInfo Extractor,
        SortedDictionary<string, string> SourceDigests,
        Diagnostics Diagnostics,
        List<ResolvedRelation> Relations,
        Authority Authority);

    private sealed record SourceTree(string RelativePath, SyntaxTree Tree, SyntaxNode Root);

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private static int Main(string[] args)
    {
        try
        {
            var values = ParseArgs(args);
            var sourceRoot = RequirePath(values, "--source-root");
            var codeFactsPath = RequirePath(values, "--code-facts");
            var output = RequirePath(values, "--out");
            ValidatePaths(sourceRoot, codeFactsPath, output);
            var facts = ReadCodeFacts(codeFactsPath);
            var overlay = Extract(sourceRoot, facts);
            Directory.CreateDirectory(Path.GetDirectoryName(output) ?? throw new InvalidOperationException("output directory is missing"));
            File.WriteAllText(output, JsonSerializer.Serialize(overlay, JsonOptions) + Environment.NewLine, new UTF8Encoding(false));
            Console.WriteLine(JsonSerializer.Serialize(new
            {
                result = "pass",
                profileId = overlay.ProfileId,
                resolvedRelationCount = overlay.Relations.Count,
                compilationErrorCount = overlay.Diagnostics.CompilationErrorCount,
                semanticResolution = true,
                sourceBuildAllowed = false,
            }, JsonOptions));
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine($"error: {error.Message}");
            return 2;
        }
    }

    private static Dictionary<string, string> ParseArgs(string[] args)
    {
        if (args.Length != 6)
        {
            throw new InvalidOperationException("expected --source-root <path> --code-facts <path> --out <path>");
        }
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var index = 0; index < args.Length; index += 2)
        {
            if (!args[index].StartsWith("--", StringComparison.Ordinal) || values.ContainsKey(args[index]) || string.IsNullOrWhiteSpace(args[index + 1]))
            {
                throw new InvalidOperationException("arguments must be unique non-empty --name value pairs");
            }
            values[args[index]] = args[index + 1];
        }
        var required = new HashSet<string>(StringComparer.Ordinal) { "--source-root", "--code-facts", "--out" };
        if (!required.SetEquals(values.Keys))
        {
            throw new InvalidOperationException("only --source-root, --code-facts, and --out are allowed");
        }
        return values;
    }

    private static string RequirePath(IReadOnlyDictionary<string, string> values, string key) =>
        Path.GetFullPath(values.TryGetValue(key, out var value) ? value : throw new InvalidOperationException($"missing {key}"));

    private static void ValidatePaths(string sourceRoot, string codeFactsPath, string output)
    {
        if (!Directory.Exists(sourceRoot) || (File.GetAttributes(sourceRoot) & FileAttributes.ReparsePoint) != 0)
        {
            throw new InvalidOperationException("source root must be an existing non-reparse-point directory");
        }
        if (!File.Exists(codeFactsPath) || (File.GetAttributes(codeFactsPath) & FileAttributes.ReparsePoint) != 0)
        {
            throw new InvalidOperationException("code facts must be a regular JSON file");
        }
        if (string.Equals(codeFactsPath, output, StringComparison.OrdinalIgnoreCase) || IsContained(output, sourceRoot))
        {
            throw new InvalidOperationException("semantic overlay output must be outside the source root and distinct from code facts");
        }
    }

    private static bool IsContained(string candidate, string parent)
    {
        var normalizedCandidate = Path.GetFullPath(candidate).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var normalizedParent = Path.GetFullPath(parent).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
        return normalizedCandidate.StartsWith(normalizedParent, StringComparison.OrdinalIgnoreCase);
    }

    private static CodeFacts ReadCodeFacts(string path)
    {
        var facts = JsonSerializer.Deserialize<CodeFacts>(File.ReadAllText(path, Encoding.UTF8), JsonOptions) ?? throw new InvalidOperationException("code facts are invalid JSON");
        if (facts.ArtifactRole != "intentgraph-code-facts" || facts.Status != "intentgraph-code-facts-extracted" || facts.Extractor.SemanticResolution || facts.Extractor.Mode != "roslyn-syntax-only" || facts.SourceRootKind != "logical-id")
        {
            throw new InvalidOperationException("code facts must be a validated syntax-only logical-source artifact");
        }
        if (!facts.SourceRoot.StartsWith("intentgraph://", StringComparison.Ordinal) || facts.SourceRoot.Contains("..", StringComparison.Ordinal) || facts.SourceRoot.Contains('\\'))
        {
            throw new InvalidOperationException("code facts logical source root is invalid");
        }
        if (facts.Facts.Count == 0 || facts.SourceDigests.Count == 0 || facts.Facts.Any(fact => string.IsNullOrWhiteSpace(fact.Id) || string.IsNullOrWhiteSpace(fact.Kind) || string.IsNullOrWhiteSpace(fact.SourceFile)))
        {
            throw new InvalidOperationException("code facts are incomplete");
        }
        return facts;
    }

    private static SemanticOverlay Extract(string sourceRoot, CodeFacts codeFacts)
    {
        var sourceFiles = Directory.EnumerateFiles(sourceRoot, "*.cs", new EnumerationOptions
        {
            RecurseSubdirectories = true,
            IgnoreInaccessible = false,
            AttributesToSkip = FileAttributes.ReparsePoint,
        })
        .Where(path => !IsExcluded(path, sourceRoot))
        .OrderBy(path => Path.GetRelativePath(sourceRoot, path), StringComparer.Ordinal)
        .ToList();

        if (sourceFiles.Count == 0 || sourceFiles.Count != codeFacts.SourceDigests.Count)
        {
            throw new InvalidOperationException("source files do not match the code-fact receipt");
        }

        var trees = new List<SourceTree>();
        foreach (var sourceFile in sourceFiles)
        {
            var relativePath = Path.GetRelativePath(sourceRoot, sourceFile).Replace(Path.DirectorySeparatorChar, '/');
            if (!codeFacts.SourceDigests.TryGetValue(relativePath, out var expectedDigest) || !string.Equals(expectedDigest, Sha256(File.ReadAllBytes(sourceFile)), StringComparison.Ordinal))
            {
                throw new InvalidOperationException($"source digest does not match code facts: {relativePath}");
            }
            var tree = CSharpSyntaxTree.ParseText(File.ReadAllText(sourceFile, Encoding.UTF8), path: relativePath, encoding: Encoding.UTF8);
            var syntaxError = tree.GetDiagnostics().FirstOrDefault(item => item.Severity == DiagnosticSeverity.Error);
            if (syntaxError is not null)
            {
                throw new InvalidOperationException($"C# syntax errors in {relativePath}: {syntaxError.Id}");
            }
            trees.Add(new SourceTree(relativePath, tree, tree.GetRoot()));
        }

        var factLocations = codeFacts.Facts
            .Where(fact => fact.SourceLocation is not null)
            .GroupBy(fact => LocationKey(fact.SourceFile, fact.Kind, fact.SourceLocation!))
            .ToDictionary(group => group.Key, group => group.Single().Id, StringComparer.Ordinal);
        var compilation = CSharpCompilation.Create(
            "IntentGraph.SemanticOverlay",
            trees.Select(item => item.Tree),
            TrustedPlatformReferences(),
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, deterministic: true));
        var diagnostics = compilation.GetDiagnostics();
        var relationPairs = new Dictionary<string, ResolvedRelation>(StringComparer.Ordinal);

        foreach (var item in trees)
        {
            var model = compilation.GetSemanticModel(item.Tree, ignoreAccessibility: true);
            foreach (var invocation in item.Root.DescendantNodes().OfType<InvocationExpressionSyntax>())
            {
                AddRelation(relationPairs, "calls", EnclosingFact(invocation, item.RelativePath, factLocations), LocalFact(model.GetSymbolInfo(invocation).Symbol, factLocations));
            }
            foreach (var creation in item.Root.DescendantNodes().OfType<ObjectCreationExpressionSyntax>())
            {
                AddRelation(relationPairs, "constructs", EnclosingFact(creation, item.RelativePath, factLocations), LocalFact(model.GetSymbolInfo(creation).Symbol, factLocations));
            }
            foreach (var identifier in item.Root.DescendantNodes().OfType<IdentifierNameSyntax>())
            {
                var symbol = model.GetSymbolInfo(identifier).Symbol;
                if (symbol is IMethodSymbol)
                {
                    continue;
                }
                AddRelation(relationPairs, "references", EnclosingFact(identifier, item.RelativePath, factLocations), LocalFact(symbol, factLocations));
            }
            foreach (var type in item.Root.DescendantNodes().OfType<BaseTypeDeclarationSyntax>())
            {
                var from = FactForNode(type, item.RelativePath, factLocations);
                foreach (var baseType in type.BaseList?.Types ?? Enumerable.Empty<BaseTypeSyntax>())
                {
                    var targetSymbol = model.GetTypeInfo(baseType.Type).Type;
                    var kind = targetSymbol?.TypeKind == TypeKind.Interface ? "implements" : "inherits";
                    AddRelation(relationPairs, kind, from, LocalFact(targetSymbol, factLocations));
                }
            }
        }

        return new SemanticOverlay(
            ArtifactRole,
            ArtifactStatus,
            ArtifactScope,
            codeFacts.ProfileId,
            codeFacts.SourceRoot,
            codeFacts.SourceRootKind,
            new ExtractorInfo(ExtractorId, ExtractorVersion, "roslyn-semantic-overlay-local-symbols", true, true, false, false),
            codeFacts.SourceDigests,
            new Diagnostics(diagnostics.Count(item => item.Severity == DiagnosticSeverity.Error), diagnostics.Count(item => item.Severity == DiagnosticSeverity.Warning), factLocations.Count),
            relationPairs.Values.OrderBy(item => item.Id, StringComparer.Ordinal).ToList(),
            new Authority(true, false, false, false, false, false, false));
    }

    private static IEnumerable<MetadataReference> TrustedPlatformReferences()
    {
        var trusted = AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES") as string;
        if (string.IsNullOrWhiteSpace(trusted))
        {
            throw new InvalidOperationException("trusted platform assembly inventory is unavailable");
        }
        return trusted.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries)
            .Where(File.Exists)
            .OrderBy(path => path, StringComparer.Ordinal)
            .Select(path => MetadataReference.CreateFromFile(path))
            .ToList();
    }

    private static void AddRelation(IDictionary<string, ResolvedRelation> relations, string kind, string? from, string? to)
    {
        if (string.IsNullOrWhiteSpace(from) || string.IsNullOrWhiteSpace(to) || string.Equals(from, to, StringComparison.Ordinal))
        {
            return;
        }
        var key = $"{kind}\u001f{from}\u001f{to}";
        relations.TryAdd(key, new ResolvedRelation($"resolved.{kind}.{Sha256(Encoding.UTF8.GetBytes(key))[7..27]}", kind, from, to, "resolved-local-symbol"));
    }

    private static string? EnclosingFact(SyntaxNode node, string sourceFile, IReadOnlyDictionary<string, string> factLocations)
    {
        foreach (var ancestor in node.AncestorsAndSelf())
        {
            var fact = FactForNode(ancestor, sourceFile, factLocations);
            if (fact is not null && KindForNode(ancestor) is "method" or "constructor" or "property" or "field")
            {
                return fact;
            }
        }
        return null;
    }

    private static string? LocalFact(ISymbol? symbol, IReadOnlyDictionary<string, string> factLocations)
    {
        if (symbol is null || symbol.Locations.All(location => !location.IsInSource))
        {
            return null;
        }
        var normalized = symbol.OriginalDefinition;
        foreach (var reference in normalized.DeclaringSyntaxReferences.OrderBy(item => item.SyntaxTree.FilePath, StringComparer.Ordinal).ThenBy(item => item.Span.Start))
        {
            var syntax = reference.GetSyntax();
            var kind = KindForNode(syntax);
            if (kind is null)
            {
                continue;
            }
            var sourceFile = syntax.SyntaxTree.FilePath.Replace('\\', '/');
            if (factLocations.TryGetValue(LocationKey(sourceFile, kind, ToLocation(syntax)), out var factId))
            {
                return factId;
            }
        }
        return null;
    }

    private static string? FactForNode(SyntaxNode node, string sourceFile, IReadOnlyDictionary<string, string> factLocations)
    {
        var kind = KindForNode(node);
        return kind is not null && factLocations.TryGetValue(LocationKey(sourceFile, kind, ToLocation(node)), out var factId) ? factId : null;
    }

    private static string? KindForNode(SyntaxNode node) => node switch
    {
        BaseTypeDeclarationSyntax => "type",
        MethodDeclarationSyntax => "method",
        ConstructorDeclarationSyntax => "constructor",
        PropertyDeclarationSyntax => "property",
        VariableDeclaratorSyntax variable when variable.Parent?.Parent is FieldDeclarationSyntax => "field",
        _ => null,
    };

    private static string LocationKey(string sourceFile, string kind, SourceLocation location) =>
        $"{sourceFile}\u001f{kind}\u001f{location.LineStart}\u001f{location.LineEnd}\u001f{location.ColumnStart}\u001f{location.ColumnEnd}";

    private static SourceLocation ToLocation(SyntaxNode node)
    {
        var span = node.GetLocation().GetLineSpan();
        return new SourceLocation(span.StartLinePosition.Line + 1, span.EndLinePosition.Line + 1, span.StartLinePosition.Character + 1, span.EndLinePosition.Character + 1);
    }

    private static bool IsExcluded(string path, string sourceRoot)
    {
        var segments = Path.GetRelativePath(sourceRoot, path).Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return segments.Any(segment => string.Equals(segment, "bin", StringComparison.OrdinalIgnoreCase) || string.Equals(segment, "obj", StringComparison.OrdinalIgnoreCase));
    }

    private static string Sha256(byte[] value) =>
        "sha256:" + Convert.ToHexString(SHA256.HashData(value)).ToLowerInvariant();
}
