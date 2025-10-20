using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace LibreOfficeAI.Models
{
    internal partial class MessageTemplateSelector : DataTemplateSelector
    {
        public DataTemplate UserTemplate { get; set; }
        public DataTemplate AITemplate { get; set; }
        public DataTemplate ErrorTemplate { get; set; }

        protected override DataTemplate SelectTemplateCore(object item)
        {
            var message = item as ChatMessage;

            return message?.Type switch
            {
                MessageType.User => UserTemplate,
                MessageType.AI => AITemplate,
                MessageType.Error => ErrorTemplate,
                _ => ErrorTemplate,
            };
        }
    }
}
