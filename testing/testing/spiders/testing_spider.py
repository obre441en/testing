import scrapy
from scrapy.crawler import CrawlerProcess
from functools import reduce
from collections import OrderedDict


class TestSpider(scrapy.Spider):
    name = "test"

    def start_requests(self):
        urls = ['https://proxyhttp.net/']
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        lines = response.css('table.proxytbl tr')
        cypher_code = response.css('script::text')[5].get()
        # I had to use [5] because there are no distinguishing features of <script>
        decrypted_values_dict = self.get_decrypted_values_dict(cypher_code)
        # convert arguments into a convenient format (dict)
        for line in lines[1:]:
            port_code_text = line.css('td.t_port script::text').get()
            clean_port = self.clear_port_text(decrypted_values_dict, port_code_text)
            yield {
                'ip_address': line.css('td.t_ip::text').get(),
                'port': clean_port
            }

    def clear_port_text(self, decrypted_values_dict, port_code_text):
        old_port_code_arguments = port_code_text.split('(')[1].split(')')[0].split('^')
        new_port_code_arguments = []

        for argument in old_port_code_arguments:
            if argument.isdigit():
                new_port_code_arguments.append(argument)
            else:
                new_port_code_arguments.append(decrypted_values_dict[argument])

        decrypted_port = str(reduce(lambda x,y: int(x)^int(y), new_port_code_arguments))
        return decrypted_port

    def get_decrypted_values_dict(self, cypher_code):
        cypher_compare_values_list = cypher_code.replace('//<![CDATA[', '').replace('//]]>', '').strip().split(';')
        cypher_values_dict = OrderedDict()

        for compare_value in cypher_compare_values_list[:-1]:
            value = compare_value.split('=')
            cypher_values_dict[value[0].strip()] = value[1].strip()

        for key in cypher_values_dict:
            raw_value = cypher_values_dict[key]
            if raw_value.isdigit():
                cypher_values_dict[key] = int(raw_value)
            elif raw_value.find('^') is not -1:
                arguments_list = raw_value.split('^')
                new_values_list = []
                for argument in arguments_list:
                    if argument.isdigit():
                        new_values_list.append(int(argument))
                    else:
                        new_values_list.append(int(cypher_values_dict[argument]))
                cypher_values_dict[key] = str(reduce(lambda x,y: x^y, new_values_list))
            else:
                cypher_values_dict[key] = cypher_values_dict[raw_value]

        return cypher_values_dict


process = CrawlerProcess(settings={
    "FEEDS": {
        "items_dict.json": {"format": "json"},
    }
})
process.crawl(TestSpider)
process.start()