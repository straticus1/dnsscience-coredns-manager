import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

export class DnsCompare implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'DNS Compare',
		name: 'dnsCompare',
		icon: 'file:dnscompare.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description: 'Compare DNS resolvers and responses',
		defaults: {
			name: 'DNS Compare',
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
						name: 'Single',
						value: 'single',
						description: 'Compare single query',
						action: 'Compare single query',
					},
					{
						name: 'Bulk',
						value: 'bulk',
						description: 'Compare multiple queries',
						action: 'Compare multiple queries',
					},
					{
						name: 'Start Shadow',
						value: 'shadowStart',
						description: 'Start shadow mode',
						action: 'Start shadow mode',
					},
					{
						name: 'Stop Shadow',
						value: 'shadowStop',
						description: 'Stop shadow mode',
						action: 'Stop shadow mode',
					},
					{
						name: 'Shadow Report',
						value: 'shadowReport',
						description: 'Get shadow mode report',
						action: 'Get shadow report',
					},
				],
				default: 'single',
			},

			// Domain for single compare
			{
				displayName: 'Domain',
				name: 'domain',
				type: 'string',
				displayOptions: {
					show: {
						operation: ['single'],
					},
				},
				default: '',
				required: true,
				description: 'Domain to compare',
			},

			// Domains for bulk compare
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
				description: 'Domains to compare (one per line)',
			},

			// Record Type
			{
				displayName: 'Record Type',
				name: 'recordType',
				type: 'options',
				displayOptions: {
					show: {
						operation: ['single', 'bulk'],
					},
				},
				options: [
					{ name: 'A', value: 'A' },
					{ name: 'AAAA', value: 'AAAA' },
					{ name: 'CNAME', value: 'CNAME' },
					{ name: 'MX', value: 'MX' },
					{ name: 'NS', value: 'NS' },
					{ name: 'TXT', value: 'TXT' },
				],
				default: 'A',
			},

			// Shadow mode options
			{
				displayName: 'Sample Rate',
				name: 'sampleRate',
				type: 'number',
				typeOptions: {
					minValue: 0,
					maxValue: 1,
				},
				displayOptions: {
					show: {
						operation: ['shadowStart'],
					},
				},
				default: 1.0,
				description: 'Query sampling rate (0-1)',
			},
			{
				displayName: 'Duration (seconds)',
				name: 'duration',
				type: 'number',
				displayOptions: {
					show: {
						operation: ['shadowStart'],
					},
				},
				default: 300,
				description: 'Shadow mode duration in seconds',
			},
			{
				displayName: 'Alert on Mismatch',
				name: 'alertOnMismatch',
				type: 'boolean',
				displayOptions: {
					show: {
						operation: ['shadowStart'],
					},
				},
				default: true,
				description: 'Whether to alert when mismatches are detected',
			},
			{
				displayName: 'Alert Threshold',
				name: 'alertThreshold',
				type: 'number',
				typeOptions: {
					minValue: 0,
					maxValue: 1,
				},
				displayOptions: {
					show: {
						operation: ['shadowStart'],
					},
				},
				default: 0.01,
				description: 'Mismatch rate threshold for alerts',
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

				if (operation === 'single') {
					endpoint = '/api/v1/compare';
					body = {
						domain: this.getNodeParameter('domain', i) as string,
						record_type: this.getNodeParameter('recordType', i) as string,
					};

				} else if (operation === 'bulk') {
					endpoint = '/api/v1/compare/bulk';
					const domainsText = this.getNodeParameter('domains', i) as string;
					const domains = domainsText.split('\n').map(d => d.trim()).filter(d => d);
					body = {
						domains,
						record_type: this.getNodeParameter('recordType', i) as string,
					};

				} else if (operation === 'shadowStart') {
					endpoint = '/api/v1/compare/shadow/start';
					body = {
						sample_rate: this.getNodeParameter('sampleRate', i) as number,
						duration_seconds: this.getNodeParameter('duration', i) as number,
						alert_on_mismatch: this.getNodeParameter('alertOnMismatch', i) as boolean,
						alert_threshold: this.getNodeParameter('alertThreshold', i) as number,
					};

				} else if (operation === 'shadowStop') {
					endpoint = '/api/v1/compare/shadow/stop';

				} else if (operation === 'shadowReport') {
					endpoint = '/api/v1/compare/shadow/report';
					method = 'GET';
				}

				const options: any = {
					method,
					uri: `${apiUrl}${endpoint}`,
					json: true,
				};

				if (method === 'POST' && Object.keys(body).length > 0) {
					options.body = body;
				}

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
