using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

internal static class Program
{
    private const string ExtractorId = "tools/csharp_syntax_probe/Program.cs";
    private const string ExtractorVersion = "0.1.0";

    private sealed record SourceLocation(int LineStart, int LineEnd, int ColumnStart, int ColumnEnd);

    private sealed record Fact(
        string Id,
        string Kind,
        string SourceFile,
        string SourceDigest,
        string Extractor,
        string ExtractorVersion,
        string Confidence,
        SourceLocation? SourceLocation = null,
        string? SourceLocationStatus = null,
        string? Name = null,
        string? DeclarationKind = null,
        string? InvocationShape = null);

    private sealed record Relation(string Id, string Kind, string From, string To);

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
        List<Fact> Facts,
        List<Relation> Relations);

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private static int Main(string[] args)
    {
        try
        {
            var values = ParseArgs(args);
            var sourceRoot = RequirePath(values, "--source-root");
            var output = RequirePath(values, "--out");
            var sourceRootId = RequireValue(values, "--source-root-id");
            ValidateLogicalSourceRoot(sourceRootId);
            ValidateSourceAndOutput(sourceRoot, output);
            var report = Extract(sourceRoot, sourceRootId);
            Directory.CreateDirectory(Path.GetDirectoryName(output) ?? throw new InvalidOperationException("output directory is missing"));
            File.WriteAllText(output, JsonSerializer.Serialize(report, JsonOptions) + Environment.NewLine, new UTF8Encoding(false));
            Console.WriteLine(JsonSerializer.Serialize(new
            {
                result = "pass",
                profileId = report.ProfileId,
                factCount = report.Facts.Count,
                relationCount = report.Relations.Count,
                sourceFileCount = report.SourceDigests.Count,
                semanticResolution = false,
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
        if (args.Length == 0 || args.Length % 2 != 0)
        {
            throw new InvalidOperationException("expected --source-root <path> --source-root-id <logical-id> --out <path>");
        }

        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var index = 0; index < args.Length; index += 2)
        {
            if (!args[index].StartsWith("--", StringComparison.Ordinal) || values.ContainsKey(args[index]))
            {
                throw new InvalidOperationException("arguments must be unique --name value pairs");
            }
            values[args[index]] = args[index + 1];
        }

        var expected = new HashSet<string>(StringComparer.Ordinal) { "--source-root", "--source-root-id", "--out" };
        if (!values.Keys.ToHashSet(StringComparer.Ordinal).SetEquals(expected))
        {
            throw new InvalidOperationException("only --source-root, --source-root-id, and --out are allowed");
        }
        return values;
    }

    private static string RequireValue(IReadOnlyDictionary<string, string> values, string key)
    {
        if (!values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"missing value for {key}");
        }
        return value;
    }

    private static string RequirePath(IReadOnlyDictionary<string, string> values, string key) =>
        Path.GetFullPath(RequireValue(values, key));

    private static void ValidateLogicalSourceRoot(string sourceRootId)
    {
        if (!sourceRootId.StartsWith("intentgraph://", StringComparison.Ordinal) || sourceRootId.Contains("..", StringComparison.Ordinal) || sourceRootId.Contains('\\'))
        {
            throw new InvalidOperationException("source root id must be an intentgraph:// logical identifier without traversal or backslashes");
        }
    }

    private static void ValidateSourceAndOutput(string sourceRoot, string output)
    {
        if (!Directory.Exists(sourceRoot))
        {
            throw new InvalidOperationException("source root must be an existing directory");
        }
        if ((File.GetAttributes(sourceRoot) & FileAttributes.ReparsePoint) != 0)
        {
            throw new InvalidOperationException("source root must not be a reparse point");
        }
        if (IsContained(output, sourceRoot))
        {
            throw new InvalidOperationException("output must not be written inside source root");
        }
    }

    private static bool IsContained(string candidate, string parent)
    {
        var normalizedCandidate = Path.GetFullPath(candidate).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var normalizedParent = Path.GetFullPath(parent).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
        return normalizedCandidate.StartsWith(normalizedParent, StringComparison.OrdinalIgnoreCase);
    }

    private static CodeFacts Extract(string sourceRoot, string sourceRootId)
    {
        var sourceFiles = Directory
            .EnumerateFiles(sourceRoot, "*.cs", new EnumerationOptions
            {
                RecurseSubdirectories = true,
                IgnoreInaccessible = false,
                AttributesToSkip = FileAttributes.ReparsePoint,
            })
            .Where(path => !IsExcluded(path, sourceRoot))
            .OrderBy(path => Path.GetRelativePath(sourceRoot, path), StringComparer.Ordinal)
            .ToList();

        if (sourceFiles.Count == 0)
        {
            throw new InvalidOperationException("no C# source files found under source root");
        }

        var facts = new List<Fact>();
        var relations = new List<Relation>();
        var digests = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var sourceFile in sourceFiles)
        {
            var relativePath = Path.GetRelativePath(sourceRoot, sourceFile).Replace(Path.DirectorySeparatorChar, '/');
            var text = File.ReadAllText(sourceFile, Encoding.UTF8);
            var tree = CSharpSyntaxTree.ParseText(text, path: relativePath, encoding: Encoding.UTF8);
            var diagnostics = tree.GetDiagnostics().Where(item => item.Severity == DiagnosticSeverity.Error).ToList();
            if (diagnostics.Count > 0)
            {
                throw new InvalidOperationException($"C# syntax errors in {relativePath}: {diagnostics[0].Id}");
            }
            var digest = Sha256(File.ReadAllBytes(sourceFile));
            digests[relativePath] = digest;
            ExtractFile(tree.GetRoot(), relativePath, digest, facts, relations);
        }

        var sortedFacts = facts.OrderBy(item => item.Id, StringComparer.Ordinal).ToList();
        var knownIds = sortedFacts.Select(item => item.Id).ToHashSet(StringComparer.Ordinal);
        var sortedRelations = relations
            .Where(item => knownIds.Contains(item.From) && knownIds.Contains(item.To))
            .OrderBy(item => item.Id, StringComparer.Ordinal)
            .ToList();
        if (sortedRelations.Count != relations.Count)
        {
            throw new InvalidOperationException("relation endpoint was not emitted as a fact");
        }

        return new CodeFacts(
            "intentgraph-code-facts",
            "intentgraph-code-facts-extracted",
            "windowsutility-csharp-syntax-only-readonly",
            "windowsutility-csharp-syntax-probe",
            "0.1.0",
            sourceRootId,
            "logical-id",
            new ExtractorInfo(ExtractorId, ExtractorVersion, "roslyn-syntax-only", true, false, false, false),
            digests,
            sortedFacts,
            sortedRelations);
    }

    private static bool IsExcluded(string path, string sourceRoot)
    {
        var segments = Path.GetRelativePath(sourceRoot, path).Split(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return segments.Any(segment => string.Equals(segment, "bin", StringComparison.OrdinalIgnoreCase) || string.Equals(segment, "obj", StringComparison.OrdinalIgnoreCase));
    }

    private static void ExtractFile(SyntaxNode root, string sourceFile, string digest, ICollection<Fact> facts, ICollection<Relation> relations)
    {
        var fileId = Id("file", sourceFile, 0, 0, sourceFile);
        facts.Add(new Fact(fileId, "file", sourceFile, digest, ExtractorId, ExtractorVersion, "extracted", SourceLocationStatus: "file-level", Name: sourceFile));
        var ids = new Dictionary<SyntaxNode, string>();
        foreach (var node in root.DescendantNodes())
        {
            switch (node)
            {
                case BaseNamespaceDeclarationSyntax namespaceNode:
                    AddNode(namespaceNode, "namespace", namespaceNode.Name.ToString(), "extracted", null, "namespace", "contains", fileId, ids, sourceFile, digest, facts, relations);
                    break;
                case BaseTypeDeclarationSyntax typeNode:
                    AddNode(typeNode, "type", typeNode.Identifier.ValueText, "extracted", null, typeNode.Kind().ToString(), "contains", fileId, ids, sourceFile, digest, facts, relations);
                    break;
                case MethodDeclarationSyntax methodNode:
                    AddNode(methodNode, "method", methodNode.Identifier.ValueText, "extracted", null, "method", "contains", fileId, ids, sourceFile, digest, facts, relations);
                    break;
                case ConstructorDeclarationSyntax constructorNode:
                    AddNode(constructorNode, "constructor", constructorNode.Identifier.ValueText, "extracted", null, "constructor", "contains", fileId, ids, sourceFile, digest, facts, relations);
                    break;
                case PropertyDeclarationSyntax propertyNode:
                    AddNode(propertyNode, "property", propertyNode.Identifier.ValueText, "extracted", null, "property", "contains", fileId, ids, sourceFile, digest, facts, relations);
                    break;
                case VariableDeclaratorSyntax variableNode when variableNode.Parent?.Parent is FieldDeclarationSyntax:
                    AddNode(variableNode, "field", variableNode.Identifier.ValueText, "extracted", null, "field", "contains", fileId, ids, sourceFile, digest, facts, relations);
                    break;
                case UsingDirectiveSyntax usingNode:
                    AddNode(usingNode, "using", usingNode.Name?.ToString() ?? string.Empty, "extracted", null, "using", "imports", fileId, ids, sourceFile, digest, facts, relations);
                    break;
                case InvocationExpressionSyntax invocationNode:
                    AddNode(invocationNode, "invocation", "invocation", "ambiguous", invocationNode.Expression.Kind().ToString(), "syntax-invocation", "invokes-syntax", fileId, ids, sourceFile, digest, facts, relations);
                    break;
            }
        }
    }

    private static void AddNode(
        SyntaxNode node,
        string kind,
        string name,
        string confidence,
        string? invocationShape,
        string declarationKind,
        string relationKind,
        string fileId,
        IDictionary<SyntaxNode, string> ids,
        string sourceFile,
        string digest,
        ICollection<Fact> facts,
        ICollection<Relation> relations)
    {
        var id = Id(kind, sourceFile, node.SpanStart, node.Span.Length, name);
        ids[node] = id;
        facts.Add(new Fact(id, kind, sourceFile, digest, ExtractorId, ExtractorVersion, confidence, ToLocation(node), Name: name, DeclarationKind: declarationKind, InvocationShape: invocationShape));
        var parentId = FindParentId(node.Parent, ids) ?? fileId;
        relations.Add(new Relation($"rel.{relationKind}.{Slug(parentId)}.{Slug(id)}", relationKind, parentId, id));
    }

    private static string? FindParentId(SyntaxNode? node, IDictionary<SyntaxNode, string> ids)
    {
        while (node is not null)
        {
            if (ids.TryGetValue(node, out var id))
            {
                return id;
            }
            node = node.Parent;
        }
        return null;
    }

    private static SourceLocation ToLocation(SyntaxNode node)
    {
        var span = node.GetLocation().GetLineSpan();
        return new SourceLocation(
            span.StartLinePosition.Line + 1,
            span.EndLinePosition.Line + 1,
            span.StartLinePosition.Character + 1,
            span.EndLinePosition.Character + 1);
    }

    private static string Id(string kind, string sourceFile, int position, int length, string name) =>
        $"csharp.{Slug(kind)}.{Slug(sourceFile)}.{position}.{length}.{Slug(name)}";

    private static string Slug(string value)
    {
        var normalized = Regex.Replace(value.ToLowerInvariant(), "[^a-z0-9]+", "_").Trim('_');
        return string.IsNullOrEmpty(normalized) ? "anonymous" : normalized;
    }

    private static string Sha256(byte[] value) =>
        "sha256:" + Convert.ToHexString(SHA256.HashData(value)).ToLowerInvariant();
}
