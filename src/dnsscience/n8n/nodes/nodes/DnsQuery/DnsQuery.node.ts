import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

export class DnsQuery implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'DNS Query',
		name: 'dnsQuery',
		icon: 'file:dnsquery.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description: 'Perform DNS queries and lookups',
		defaults: {
			name: 'DNS Query',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'dnsScienceApi',
				required: true,
			},
		],
		properties: [
			// Operation
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'Lookup',
						value: 'lookup',
						description: 'Perform DNS lookup',
						action: 'Perform DNS lookup',
					},
					{
						name: 'Bulk Lookup',
						value: 'bulk',
						description: 'Perform multiple DNS lookups',
						action: 'Perform bulk DNS lookup',
					},
					{
						name: 'Trace',
						value: 'trace',
						description: 'Trace DNS resolution path',
						action: 'Trace DNS resolution',
					},
					{
						name: 'Benchmark',
						value: 'benchmark',
						description: 'Benchmark DNS performance',
						action: 'Benchmark DNS performance',
					},
				],
				default: 'lookup',
			},

			// Domain for single lookup
			{
				displayName: 'Domain',
				name: 'domain',
				type: 'string',
				displayOptions: {
					show: {
						operation: ['lookup', 'trace', 'benchmark'],
					},
				},
				default: '',
				required: true,
				description: 'Domain name to query',
				placeholder: 'example.com',
			},

			// Domains for bulk lookup
			{
				displayName: 'Domains',
				name: 'domains',
				type: 'string',
				typeOptions: {
					rows: 5,
				},
				displayOptions: {
					show: {
						operation: ['bulk'],
					},
				},
				default: '',
				required: true,
				description: 'Domain names to query (one per line)',
				placeholder: 'example.com\ngoogle.com\ncloudflare.com',
			},

			// Record Type
			{
				displayName: 'Record Type',
				name: 'recordType',
				type: 'options',
				options: [
					{ name: 'A', value: 'A' },
					{ name: 'AAAA', value: 'AAAA' },
					{ name: 'CNAME', value: 'CNAME' },
					{ name: 'MX', value: 'MX' },
					{ name: 'NS', value: 'NS' },
					{ name: 'TXT', value: 'TXT' },
					{ name: 'SOA', value: 'SOA' },
					{ name: 'PTR', value: 'PTR' },
					{ name: 'SRV', value: 'SRV' },
				],
				default: 'A',
				description: 'DNS record type to query',
			},

			// DNSSEC
			{
				displayName: 'DNSSEC Validation',
				name: 'dnssec',
				type: 'boolean',
				default: false,
				description: 'Whether to request DNSSEC validation',
			},

			// Custom DNS Server
			{
				displayName: 'DNS Server',
				name: 'server',
				type: 'string',
				default: '',
				description: 'Custom DNS server to query (optional)',
				placeholder: '8.8.8.8',
			},

			// Benchmark options
			{
				displayName: 'Query Count',
				name: 'count',
				type: 'number',
				displayOptions: {
					show: {
						operation: ['benchmark'],
					},
				},
				default: 100,
				description: 'Number of queries for benchmark',
			},
			{
				displayName: 'Concurrency',
				name: 'concurrency',
				type: 'number',
				displayOptions: {
					show: {
						operation: ['benchmark'],
					},
				},
				default: 10,
				description: 'Number of concurrent queries',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];
		const credentials = await this.getCredentials('dnsScienceApi');

		const operation = this.getNodeParameter('operation', 0) as string;
		const apiUrl = credentials.apiUrl as string;

		for (let i = 0; i < items.length; i++) {
			try {
				let endpoint = '';
				let method = 'POST';
				let body: any = {};

				const recordType = this.getNodeParameter('recordType', i) as string;
				const dnssec = this.getNodeParameter('dnssec', i) as boolean;
				const server = this.getNodeParameter('server', i) as string;

				if (operation === 'lookup') {
					endpoint = '/api/v1/query';
					body = {
						name: this.getNodeParameter('domain', i) as string,
						record_type: recordType,
						dnssec: dnssec,
					};
					if (server) body.server = server;

				} else if (operation === 'bulk') {
					endpoint = '/api/v1/query/bulk';
					const domainsText = this.getNodeParameter('domains', i) as string;
					const domains = domainsText.split('\n').map(d => d.trim()).filter(d => d);
					body = {
						queries: domains.map(domain => ({
							name: domain,
							record_type: recordType,
							dnssec: dnssec,
						})),
					};

				} else if (operation === 'trace') {
					endpoint = '/api/v1/query/trace';
					body = {
						name: this.getNodeParameter('domain', i) as string,
						record_type: recordType,
					};

				} else if (operation === 'benchmark') {
					endpoint = '/api/v1/query/bench';
					body = {
						name: this.getNodeParameter('domain', i) as string,
						count: this.getNodeParameter('count', i) as number,
						concurrency: this.getNodeParameter('concurrency', i) as number,
					};
				}

				const options: any = {
					method,
					uri: `${apiUrl}${endpoint}`,
					body,
					json: true,
				};

				if (credentials.apiKey) {
					options.headers = {
						'Authorization': `Bearer ${credentials.apiKey}`,
					};
				}

				const response = await this.helpers.request(options);

				returnData.push({
					json: response,
					pairedItem: { item: i },
				});

			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: { error: error.message },
						pairedItem: { item: i },
					});
					continue;
				}
				throw new NodeOperationError(this.getNode(), error, { itemIndex: i });
			}
		}

		return [returnData];
	}
}
