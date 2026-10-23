export const convertToPythonVariableName = (str: string): string => {
    if (!str) return ''

    // Replace spaces and hyphens with underscores
    str = str.replace(/[\s-]/g, '_')

    // Remove any non-alphanumeric characters except underscores
    str = str.replace(/[^a-zA-Z0-9_]/g, '')

    // Add underscore prefix only if first char is a number
    if (/^[0-9]/.test(str)) {
        str = '_' + str
    }

    return str
}
