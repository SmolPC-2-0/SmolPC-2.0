using LibreOfficeAI.Services;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace LibreOfficeAI.Models
{
    internal partial class DocTemplateSelector : DataTemplateSelector
    {
        public DataTemplate WriterDocTemplate { get; set; }
        public DataTemplate ImpressDocTemplate { get; set; }

        protected override DataTemplate SelectTemplateCore(object item)
        {
            var document = item as Document;

            return document?.DocType switch
            {
                DocType.Writer => WriterDocTemplate,
                DocType.Impress => ImpressDocTemplate,
                _ => WriterDocTemplate,
            };
        }
    }
}
