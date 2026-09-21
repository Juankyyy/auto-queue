<#
.SYNOPSIS
  Genera RELEASE_NOTES.md para un tag: mensaje del tag + lista de commits.
.PARAMETER Tag
  Tag a publicar (ej. 0.2.0).
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Tag
)

$ErrorActionPreference = "Stop"

# Notas personalizadas = mensaje del tag anotado (lo escribe Auto Release)
$tagMsg = (git tag -l --format='%(contents)' $Tag | Out-String).Trim()
# Tag anterior para listar solo los cambios nuevos
$prev = (git describe --tags --abbrev=0 "$Tag^" 2>$null | Out-String).Trim()
if ($prev) { $range = "$prev..$Tag" } else { $range = $Tag }
$log = (git log $range --pretty=format:'- %s (%h)' --reverse | Out-String).Trim()
$body = ""
if ($tagMsg) { $body += "## Novedades`r`n`r`n$tagMsg`r`n`r`n" }
$body += "## Cambios`r`n`r`n$log"
Set-Content -Path RELEASE_NOTES.md -Value $body -Encoding UTF8
Get-Content RELEASE_NOTES.md
